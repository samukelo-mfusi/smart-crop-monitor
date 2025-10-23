from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
import secrets
import logging
from typing import Optional
import sendgrid
from ...database.database import get_db
from ...database.crud import get_user_by_username, create_user, get_user_by_email, update_user_password
from ...core.security import authenticate_user, create_access_token, get_password_hash, get_current_user, \
    validate_password_strength, generate_secure_token
from ...core.config import settings
from ...database.models import User

router = APIRouter()
logger = logging.getLogger(__name__)


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str


class UserResponse(BaseModel):
    username: str
    email: str
    full_name: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    message: str
    status: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenValidationResponse(BaseModel):
    valid: bool
    email: Optional[str] = None


reset_tokens_store = {}
refresh_tokens_store = {}


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    password_validation = validate_password_strength(user_data.password)
    if not password_validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=password_validation["message"]
        )

    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password=user_data.password
    )

    return UserResponse(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active
    )


@router.post("/login", response_model=Token)
def login_for_access_token(
        login_data: LoginRequest,
        db: Session = Depends(get_db)
):
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if login_data.remember_me:
        access_token_expires = timedelta(days=7)
        refresh_token_expires = timedelta(days=30)
    else:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=7)

    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    refresh_token = generate_secure_token(64)

    refresh_tokens_store[refresh_token] = {
        "username": user.username,
        "expires": datetime.utcnow() + refresh_token_expires,
        "created_at": datetime.utcnow()
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds())
    }


@router.post("/token", response_model=Token)
def login_for_access_token_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    refresh_token = generate_secure_token(64)
    refresh_token_expires = timedelta(days=1)

    refresh_tokens_store[refresh_token] = {
        "username": user.username,
        "expires": datetime.utcnow() + refresh_token_expires,
        "created_at": datetime.utcnow()
    }

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds())
    }


@router.post("/refresh", response_model=Token)
def refresh_access_token(request: RefreshTokenRequest):
    try:
        refresh_token = request.refresh_token

        if refresh_token not in refresh_tokens_store:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        token_data = refresh_tokens_store[refresh_token]

        if datetime.utcnow() > token_data["expires"]:
            del refresh_tokens_store[refresh_token]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )

        username = token_data["username"]

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )

        new_refresh_token = generate_secure_token(64)
        refresh_token_expires = timedelta(days=30)

        refresh_tokens_store[new_refresh_token] = {
            "username": username,
            "expires": datetime.utcnow() + refresh_token_expires,
            "created_at": datetime.utcnow()
        }

        del refresh_tokens_store[refresh_token]

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error refreshing token"
        )


@router.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active
    )


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
        request: ForgotPasswordRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_email(db, request.email)
        if not user:
            logger.info(f"Password reset requested for non-existent email: {request.email}")
            return PasswordResetResponse(
                message="If the email exists, a password reset link has been sent",
                status="success"
            )

        reset_token = generate_secure_token(64)
        reset_token_expires = datetime.utcnow() + timedelta(hours=settings.RESET_TOKEN_EXPIRE_HOURS)

        reset_tokens_store[reset_token] = {
            "user_id": user.id,
            "email": user.email,
            "expires": reset_token_expires,
            "used": False,
            "created_at": datetime.utcnow()
        }

        background_tasks.add_task(send_password_reset_email, user.email, reset_token)

        logger.info(f"Password reset token generated for user: {user.email}")

        return PasswordResetResponse(
            message="If the email exists, a password reset link has been sent",
            status="success"
        )

    except Exception as e:
        logger.error(f"Error in forgot password: {e}")
        return PasswordResetResponse(
            message="An error occurred. Please try again later.",
            status="error"
        )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
        request: ResetPasswordRequest,
        db: Session = Depends(get_db)
):
    try:
        if request.token not in reset_tokens_store:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        token_data = reset_tokens_store[request.token]

        if datetime.utcnow() > token_data["expires"]:
            del reset_tokens_store[request.token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )

        if token_data["used"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has already been used"
            )

        user = db.query(User).filter(User.id == token_data["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )

        password_validation = validate_password_strength(request.new_password)
        if not password_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=password_validation["message"]
            )

        update_user_password(db, user.id, request.new_password)

        token_data["used"] = True
        reset_tokens_store[request.token] = token_data

        cleanup_old_tokens_for_user(user.id)

        logger.info(f"Password successfully reset for user: {user.email}")

        return PasswordResetResponse(
            message="Password has been reset successfully",
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password"
        )


@router.post("/validate-reset-token", response_model=TokenValidationResponse)
async def validate_reset_token(token: str):
    try:
        if token not in reset_tokens_store:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )

        token_data = reset_tokens_store[token]

        if datetime.utcnow() > token_data["expires"]:
            del reset_tokens_store[token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )

        if token_data["used"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has already been used"
            )

        return TokenValidationResponse(valid=True, email=token_data["email"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating reset token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating token"
        )


def send_password_reset_email(email: str, token: str):
    try:
        reset_url = f"{settings.FRONTEND_URL}/?token={token}"

        subject = "Password Reset Request - Smart Crop Monitoring"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #3498db;
                         color: white; text-decoration: none; border-radius: 4px; font-weight: bold; }}
                .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                .code {{ background: #f4f4f4; padding: 10px; border-radius: 4px; font-family: monospace; word-break: break-all; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>You requested to reset your password for your Smart Crop Monitoring account.</p>
                <p>Click the button below to create a new password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link in your browser:</p>
                <div class="code">{reset_url}</div>
                <p><strong>This link will expire in {settings.RESET_TOKEN_EXPIRE_HOURS} hours.</strong></p>
                <div class="footer">
                    <p>If you didn't request this reset, please ignore this email and your password will remain unchanged.</p>
                    <p>For security reasons, do not share this email with anyone.</p>
                </div>
            </div>
        </body>
        </html>
        """

        if settings.EMAIL_ENABLED and settings.SENDGRID_API_KEY:
            logger.info(f"Attempting to send email to {email} using SendGrid")

            sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)

            # Create email data
            data = {
                "personalizations": [
                    {
                        "to": [{"email": email}],
                        "subject": subject
                    }
                ],
                "from": {"email": settings.FROM_EMAIL, "name": "Smart Crop Monitoring"},
                "content": [
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }

            try:
                response = sg.client.mail.send.post(request_body=data)
                logger.info(f"SendGrid response status: {response.status_code}")
                logger.info(f"SendGrid response headers: {response.headers}")

                if response.status_code in [200, 202]:
                    logger.info(f"Password reset email successfully sent to {email}")
                    return True
                else:
                    logger.error(f"SendGrid returned status {response.status_code}")
                    logger.error(f"SendGrid response body: {response.body}")
                    return False

            except Exception as sendgrid_error:
                logger.error(f"SendGrid API error: {str(sendgrid_error)}")
                return False

        else:
            # Email not enabled or no API key
            logger.warning(f"Email sending disabled. Reset link for {email}: {reset_url}")
            logger.warning(
                f"EMAIL_ENABLED: {settings.EMAIL_ENABLED}, SENDGRID_API_KEY: {'Set' if settings.SENDGRID_API_KEY else 'Not Set'}")
            return True  # Return True so user doesn't know email failed

    except Exception as e:
        logger.error(f"Error in send_password_reset_email: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

def cleanup_old_tokens_for_user(user_id: int):
    tokens_to_remove = []
    for token, data in reset_tokens_store.items():
        if data["user_id"] == user_id and (data["used"] or datetime.utcnow() > data["expires"]):
            tokens_to_remove.append(token)

    for token in tokens_to_remove:
        del reset_tokens_store[token]


@router.post("/logout")
def logout(refresh_token: str):
    if refresh_token in refresh_tokens_store:
        del refresh_tokens_store[refresh_token]

    return {"message": "Successfully logged out"}