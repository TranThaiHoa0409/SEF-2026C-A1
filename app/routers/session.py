"""Đăng nhập bằng cách chọn tài khoản mẫu."""
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Response
from pydantic import BaseModel

from .. import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    user_id: str


@router.get("/accounts")
def accounts():
    """Danh sách tài khoản mẫu để chọn (không cần đăng nhập)."""
    return auth.list_accounts()


@router.post("/login")
def login(body: LoginBody, response: Response):
    token, user = auth.login(body.user_id)
    response.set_cookie(auth.COOKIE_NAME, token, httponly=True, samesite="lax")
    return user


@router.post("/logout")
def logout(response: Response, bb_session: Optional[str] = Cookie(default=None)):
    auth.logout(bb_session)
    response.delete_cookie(auth.COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(auth.current_user)):
    return user
