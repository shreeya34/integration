class IntegrationError(Exception):

    pass


class OAuthError(IntegrationError):

    def __init__(self, message: str = "OAuth authentication failed", *args):
        super().__init__(message, *args)


class TokenRefreshError(OAuthError):

    def __init__(self, message: str = "Failed to refresh access token", *args):
        super().__init__(message, *args)


class InvalidStateError(OAuthError):

    def __init__(self, message: str = "State parameter mismatch", *args):
        super().__init__(message, *args)


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
