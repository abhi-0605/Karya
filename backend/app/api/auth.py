"""Demo auth — JWT with hard-coded demo users. NOT for production."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Demo users (synthetic, no real PII)
DEMO_USERS: dict[str, dict] = {
    "employee1":  {"password": "demo", "role": "employee",  "person_id": "EMP001", "name": "Arjun Sharma"},
    "manager1":   {"password": "demo", "role": "manager",   "person_id": "MGR001", "name": "Priya Nair"},
    "hrbp1":      {"password": "demo", "role": "hrbp",      "person_id": "HRB001", "name": "Deepa Menon"},
    "hr_head1":   {"password": "demo", "role": "hr_head",   "person_id": "HRH001", "name": "Vikram Rao"},
    "it_ops1":    {"password": "demo", "role": "it_ops",    "person_id": "ITO001", "name": "Ravi Kumar"},
    "finance1":   {"password": "demo", "role": "finance",   "person_id": "FIN001", "name": "Ananya Iyer"},
    "auditor1":   {"password": "demo", "role": "auditor",   "person_id": "AUD001", "name": "Suresh Pillai"},
    "admin_ops1": {"password": "demo", "role": "admin_ops", "person_id": "ADM001", "name": "Meera Krishnan"},
}


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    name: str


def create_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("/token", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = DEMO_USERS.get(form.username)
    if not user or user["password"] != form.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    token = create_token({
        "sub": form.username,
        "role": user["role"],
        "person_id": user["person_id"],
        "name": user["name"],
        "principal_type": "human",
    })
    return Token(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        name=user["name"],
    )


@router.get("/me")
async def me(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return user
