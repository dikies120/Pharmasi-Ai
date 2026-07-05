from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from back.app.controllers.auth_controller import AuthController


router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_controller = AuthController()


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    nik: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    email: str
    new_password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    try:
        result = await auth_controller.register(
            name=request.name,
            email=request.email,
            password=request.password,
            role="patient",
            nik=request.nik
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login")
async def login(request: LoginRequest):
    try:
        result = await auth_controller.login(
            email=request.email,
            password=request.password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest):
    try:
        result = await auth_controller.change_password(
            email=request.email,
            new_password=request.new_password
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/logout")
async def logout():
    return {"message": "Logout berhasil"}
