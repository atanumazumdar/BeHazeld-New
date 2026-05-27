class AppError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class InvalidCredentialsError(AppError):
    status_code = 401
    error_code = "INVALID_CREDENTIALS"
    message = "Invalid credentials"


class PermissionDeniedError(AppError):
    status_code = 403
    error_code = "PERMISSION_DENIED"
    message = "Permission denied"


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource already exists"


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation error"


class TenantNotFoundError(NotFoundError):
    error_code = "TENANT_NOT_FOUND"
    message = "Tenant not found"


class LastAdminError(ConflictError):
    error_code = "LAST_ADMIN_ERROR"
    message = "Cannot deactivate the last active admin user of a tenant"


class StockNotAvailableError(AppError):
    status_code = 409
    error_code = "SALE_STOCK_NOT_AVAILABLE"
    message = "Stock is not available for one or more items"


class UnbalancedJournalError(AppError):
    status_code = 422
    error_code = "FINANCE_UNBALANCED_ENTRY"
    message = "Journal entry debits and credits do not balance"
