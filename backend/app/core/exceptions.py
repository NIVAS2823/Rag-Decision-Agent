"""
Custom Exceptions
=================
Application-specific exception classes.
"""

from fastapi import HTTPException, status


class AuthenticationException(HTTPException):
    """Base authentication exception"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidCredentialsException(AuthenticationException):
    """Invalid username or password"""
    def __init__(self):
        super().__init__(detail="Incorrect email or password")


class TokenExpiredException(AuthenticationException):
    """Token has expired"""
    def __init__(self):
        super().__init__(detail="Token has expired")


class InvalidTokenException(AuthenticationException):
    """Token is invalid"""
    def __init__(self):
        super().__init__(detail="Could not validate credentials")


class TokenRevokedException(AuthenticationException):
    """Token has been revoked"""
    def __init__(self):
        super().__init__(detail="Token has been revoked")


class InsufficientPermissionsException(HTTPException):
    """User lacks required permissions"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )


class UserNotFoundException(HTTPException):
    """User not found"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


class UserInactiveException(AuthenticationException):
    """User account is inactive"""
    def __init__(self):
        super().__init__(detail="User account is inactive")