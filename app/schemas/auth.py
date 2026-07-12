from pydantic import EmailStr, Field, SecretStr

from app.schemas.base import StrictRequestModel


class LoginRequest(StrictRequestModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
