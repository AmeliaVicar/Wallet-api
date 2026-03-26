from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.wallet import (
    WalletOperationRequest,
    WalletOperationResponse,
    WalletResponse,
)
from app.services.wallet import wallet_service

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> WalletResponse:
    wallet = await wallet_service.get_wallet(session=session, wallet_id=wallet_id)
    return WalletResponse(wallet_id=wallet.id, balance=wallet.balance)


@router.post("/{wallet_id}/operation", response_model=WalletOperationResponse)
async def operate_wallet(
    wallet_id: UUID,
    payload: WalletOperationRequest,
    session: AsyncSession = Depends(get_session),
) -> WalletOperationResponse:
    result = await wallet_service.apply_operation(
        session=session,
        wallet_id=wallet_id,
        operation_type=payload.operation_type,
        amount=payload.amount,
    )
    return WalletOperationResponse(
        wallet_id=result.wallet.id,
        balance=result.wallet.balance,
        operation_type=result.operation_type,
        amount=result.amount,
    )

