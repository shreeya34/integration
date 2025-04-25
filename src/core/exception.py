class IntegrationError(Exception):

    pass


class OAuthError(IntegrationError):
    def __init__(self, message: str = "OAuth authentication failed", *args):
        super().__init__(message, *args)


class TokenRefreshError(OAuthError):
    def __init__(self, message: str = "Failed to refresh access token", *args):
        super().__init__(message, *args)


class InvalidStateError(Exception):
    """Exception raised when the state parameter doesn't match."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)



class TokenExchangeError(OAuthError):
    def __init__(
        self, message: str = "Failed to exchange authorization code for tokens", *args
    ):
        super().__init__(message, *args)


class TokenRevocationError(OAuthError):
    def __init__(self, message: str = "Failed to revoke token", *args):
        super().__init__(message, *args)


class APIRequestError(IntegrationError):
    def __init__(
        self, message: str = "API request failed", status_code: int = None, *args
    ):
        self.status_code = status_code
        super().__init__(message, *args)

class UnsupportedCRMError(APIRequestError):
    def __init__(self, crm_name: str):
        self.crm_name = crm_name
        super().__init__(f"Unsupported CRM: {crm_name}")
        
class CRMIntegrationError(APIRequestError):
    def __init__(self, message: str):
        super().__init__(message)