from fastapi import APIRouter, Depends, HTTPException
from sqlAlchemy.orm import Session

from app.db.models.connection import get_session
from app.db.repositories.user_repository import UserRepository
from app.api.schemas.classroom import Classroom
from app.api.schemas.user import User as UserSchema
from app.api.schemas.user import UserCreate

router = APIRouter()

@router