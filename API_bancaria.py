from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import List, Optional
import jose.jwt as jwt

SECRET_KEY = "sua_chave_secreta_super_segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="DIO Bank API")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

db_users = {"joao": {"username": "joao", "password": "123", "balance": 1000.0}}
db_transactions = [] 

class TransactionBase(BaseModel):
    amount: float = Field(..., gt=0, description="O valor deve ser maior que zero")

class TransactionOut(BaseModel):
    type: str
    amount: float
    timestamp: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in db_users:
            raise HTTPException(status_code=401, detail="Usuário inválido")
        return db_users[username]
    except:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db_users.get(form_data.username)
    if not user or form_data.password != user["password"]:
        raise HTTPException(status_code=400, detail="Usuário ou senha incorretos")
    
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/conta/deposito")
async def depositar(data: TransactionBase, user: dict = Depends(get_current_user)):
    user["balance"] += data.amount
    transaction = {"user": user["username"], "type": "DEPOSITO", "amount": data.amount, "timestamp": datetime.now()}
    db_transactions.append(transaction)
    return {"message": "Depósito realizado", "novo_saldo": user["balance"]}

@app.post("/conta/saque")
async def sacar(data: TransactionBase, user: dict = Depends(get_current_user)):
    if data.amount > user["balance"]:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")
    
    user["balance"] -= data.amount
    transaction = {"user": user["username"], "type": "SAQUE", "amount": data.amount, "timestamp": datetime.now()}
    db_transactions.append(transaction)
    return {"message": "Saque realizado", "novo_saldo": user["balance"]}

@app.get("/conta/extrato", response_model=List[TransactionOut])
async def ver_extrato(user: dict = Depends(get_current_user)):
    # Filtra transações apenas do usuário logado
    extrato = [t for t in db_transactions if t["user"] == user["username"]]
    return extrato
