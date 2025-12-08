from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from config.settings import settings
from models.user import UserInDB, UserRole
from services.repositories.user_repo import UserRepository 

from services.dependencies import get_user_repo_dependency, get_settings 
from config.settings import Settings 

# ----------------- HASHING -----------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    truncated_password = plain_password[:72] 
    
    return pwd_context.verify(truncated_password, hashed_password)

def get_password_hash(password):
    truncated_password = password[:72] 
    return pwd_context.hash(truncated_password)

# ----------------- JWT (JSON Web Tokens) -----------------
SECRET_KEY = settings.SECRET_KEY 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ----------------- AUTH DEPENDENCIES -----------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_user_repo_dependency(request: Request) -> UserRepository:
    """Retrieves the UserRepository instance from the FastAPI app state."""
    return request.app.state.user_repo

# DEFINITION OF THE FUNCTION TO GET THE CURRENT USER
async def get_current_user_doc(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)]
) -> UserInDB:
    """Dependency to retrieve the UserInDB object from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await user_repo.get_user_by_email(user_email)
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_admin(current_user: Annotated[UserInDB, Depends(get_current_user_doc)]) -> UserInDB:
    """Dependency to check if the current user is an active 'admin'."""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have administrative privileges"
        )
    return current_user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo_dependency)],
    settings: Annotated[Settings, Depends(get_settings)] 
) -> UserInDB:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
    except (JWTError, AttributeError):
        raise credentials_exception

    user_doc = await user_repo.get_user_by_email(email)
    
    if user_doc is None:
        raise credentials_exception
        
    return user_doc