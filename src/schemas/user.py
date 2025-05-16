# src/schemas/user.py
from pydantic import BaseModel, EmailStr, constr


# Shared base
class UserBase(BaseModel):
    email: EmailStr


# Create user
class UserCreate(UserBase):
    password: str


# Login user
class UserLogin(UserBase):
    password: str


# Response token
class Token(BaseModel):
    access_token: str
    token_type: str


# User data returned (e.g., in /me endpoint)
class UserOut(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True  # for ORM mode in Pydantic v2+


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordChange(BaseModel):
    old_password: constr(min_length=8) # type: ignore
    new_password: constr(min_length=8) # type: ignore
