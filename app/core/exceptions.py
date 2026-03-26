from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400
    detail = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)

    @staticmethod
    async def handler(_: Request, exc: "AppError") -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled application error",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


class WalletNotFoundError(AppError):
    status_code = 404
    detail = "Wallet not found"


class InvalidOperationTypeError(AppError):
    status_code = 400
    detail = "Invalid operation type"


class InvalidAmountError(AppError):
    status_code = 400
    detail = "Amount must be greater than zero"


class AmountTooLargeError(AppError):
    status_code = 400
    detail = "Amount exceeds the maximum supported value"


class InsufficientFundsError(AppError):
    status_code = 409
    detail = "Insufficient funds"


class BalanceLimitExceededError(AppError):
    status_code = 409
    detail = "Balance limit exceeded"
