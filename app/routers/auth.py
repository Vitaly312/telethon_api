from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from telethon import errors as telethon_errors
from .utils import TelegramClientsRepository, TelegramBaseClient
import jwt
from jwt.exceptions import InvalidTokenError
from config import SECRET_KEY, ALGORITHM


class AuthCodeData(BaseModel):
    api_id: int
    api_hash: str
    phone: str

class Token(BaseModel):
    token: str

class AnswerphoneData(Token):
    text: str

class AuthData(BaseModel):
    client_id: str
    msg_code: str
    phone: str
    password: str = None

class AuthCodeDataOut(BaseModel):
    client_id: str

router = APIRouter()
telegram_clients_repository = TelegramClientsRepository()


@router.post('/api/auth_request/')
async def send_auth_request(auth_data: AuthCodeData) -> AuthCodeDataOut:
    client = telegram_clients_repository.add_client(auth_data.api_id, auth_data.api_hash)
    try:
        await client.send_code(auth_data.phone)
    except telethon_errors.FloodWaitError as e:
        return {
            'FloodWaitError': {
                'phone_number': e.request.phone_number,
                'seconds': e.seconds
            }}
    except telethon_errors.rpcerrorlist.ApiIdInvalidError:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API ID or API HASH is invalid",
    )
    return AuthCodeDataOut(client_id=client.session_id)


def generate_jwt(payload: dict):
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/api/auth/")
async def auth(auth_data: AuthData):
    client = telegram_clients_repository.get_client(auth_data.client_id)
    if not client:
        return {"status": 'error', 'message': 'Invalid client ID'}
    try:
        await client.connect(phone=auth_data.phone, code=auth_data.msg_code,
                            password=auth_data.password)
    except telethon_errors.rpcerrorlist.PhoneCodeInvalidError:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="The phone code entered was invalid",
    )
    payload = {'client_id': client.session_id, 'permissions': 'ALL'}
    return generate_jwt(payload)


def get_client_by_jwt(token: str) -> TelegramBaseClient:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
    except InvalidTokenError:
        raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    client = telegram_clients_repository.get_client(payload['client_id'])
    if not client or payload['permissions'] != 'ALL':
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Could not found this telegram client",
    )
    return client

@router.post('/api/answerphone/')
async def enable_answerphone(data: AnswerphoneData):
    client = get_client_by_jwt(data.token)
    client.text = data.text

@router.delete('/api/answerphone/')
async def disable_answerphone(token: Token):
    client = get_client_by_jwt(token.token)
    client.text = None