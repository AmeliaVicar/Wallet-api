from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import POSTGRES_BIGINT_MAX
from app.core.exceptions import (
    AmountTooLargeError,
    BalanceLimitExceededError,
    InsufficientFundsError,
    InvalidAmountError,
    InvalidOperationTypeError,
    WalletNotFoundError,
)
from app.db.models.wallet import Wallet
from app.repositories.wallet import wallet_repository


class OperationType(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


@dataclass(slots=True)
class WalletOperationResult:
    wallet: Wallet
    operation_type: str
    amount: int


class WalletService:
    async def get_wallet(self, session: AsyncSession, wallet_id: UUID) -> Wallet:
        wallet = await wallet_repository.get_by_id(session=session, wallet_id=wallet_id)
        if wallet is None:
            raise WalletNotFoundError()
        return wallet

    async def apply_operation(
        self,
        session: AsyncSession,
        wallet_id: UUID,
        operation_type: str,
        amount: int,
    ) -> WalletOperationResult:
        parsed_operation = self._parse_operation_type(operation_type)
        self._validate_amount(amount)

        async with session.begin():
            wallet = await wallet_repository.get_by_id(
                session=session,
                wallet_id=wallet_id,
                for_update=True,
            )
            if wallet is None:
                raise WalletNotFoundError()

            if parsed_operation == OperationType.DEPOSIT:
                if wallet.balance > POSTGRES_BIGINT_MAX - amount:
                    raise BalanceLimitExceededError()
                wallet.balance += amount
            else:
                if wallet.balance < amount:
                    raise InsufficientFundsError()
                wallet.balance -= amount

            await session.flush()

        return WalletOperationResult(
            wallet=wallet,
            operation_type=parsed_operation.value,
            amount=amount,
        )

    @staticmethod
    def _parse_operation_type(operation_type: str) -> OperationType:
        try:
            return OperationType(operation_type)
        except ValueError as exc:
            raise InvalidOperationTypeError() from exc

    @staticmethod
    def _validate_amount(amount: int) -> None:
        if amount <= 0:
            raise InvalidAmountError()
        if amount > POSTGRES_BIGINT_MAX:
            raise AmountTooLargeError()


wallet_service = WalletService()
