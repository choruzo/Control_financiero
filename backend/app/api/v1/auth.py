from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import RefreshRequest, Token, UserCreate, UserResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)) -> Token:
    """Register a new user and return an access/refresh token pair."""
    user = await auth_service.create_user(db, body.email, body.password)
    return await auth_service.issue_tokens(db, user)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate with email + password and return a token pair."""
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    return await auth_service.issue_tokens(db, user)


@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Exchange a valid refresh token for a new access/refresh token pair."""
    return await auth_service.rotate_refresh_token(db, body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's profile."""
    return current_user
