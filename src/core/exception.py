from fastapi import HTTPException
from fastapi import status
from typing import Optional, Any


class IntegrationError(HTTPException):
    """Base exception for all integration-related errors"""

    def __init__(
        self,
        detail: str = "Integration error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: Optional[dict] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.extra_data = kwargs


class OAuthError(IntegrationError):
    """Base exception for OAuth 2.0 related errors"""

    def __init__(
        self,
        detail: str = "OAuth authentication failed",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class TokenRefreshError(OAuthError):
    """Failed to refresh access token"""

    def __init__(
        self,
        detail: str = "Failed to refresh access token",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class InvalidStateError(OAuthError):
    def __init__(
        self,
        detail: str = "Invalid state parameter",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class TokenExchangeError(OAuthError):
    def __init__(
        self,
        detail: str = "Failed to exchange authorization code",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class TokenRevocationError(OAuthError):
    def __init__(
        self,
        detail: str = "Failed to revoke token",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class APIRequestError(IntegrationError):
    """Base exception for API request failures"""

    def __init__(
        self,
        detail: str = "API request failed",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class UnsupportedCRMError(APIRequestError):
    """Unsupported CRM requested"""

    def __init__(
        self,
        crm_name: str,
        detail: Optional[str] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs,
    ) -> None:
        detail = detail or f"Unsupported CRM: {crm_name}"
        self.crm_name = crm_name
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class CRMIntegrationError(APIRequestError):
    """General CRM integration error"""

    def __init__(
        self,
        detail: str = "CRM integration error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class InvalidPageNumberError(IntegrationError):
    """Invalid pagination parameter"""

    def __init__(
        self,
        detail: str = "Invalid page number",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)


class ContactsFetchError(CRMIntegrationError):
    """Failed to fetch contacts from CRM"""

    def __init__(
        self,
        detail: str = "Failed to fetch contacts",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        **kwargs,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code, **kwargs)
