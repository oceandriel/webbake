from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
