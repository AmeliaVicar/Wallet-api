from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.wallet import Wallet


class WalletRepository:
    async def get_by_id(
        self,
        session: AsyncSession,
        wallet_id: UUID,
        *,
        for_update: bool = False,
    ) -> Wallet | None:
        statement = select(Wallet).where(Wallet.id == wallet_id)
        if for_update:
            statement = statement.with_for_update()

        result = await session.execute(statement)
        return result.scalar_one_or_none()


wallet_repository = WalletRepository()

