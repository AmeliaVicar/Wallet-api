from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import POSTGRES_BIGINT_MAX

AmountValue = Annotated[int, Field(le=POSTGRES_BIGINT_MAX)]


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    wallet_id: UUID
    balance: int


class WalletOperationRequest(BaseModel):
    operation_type: str
    amount: AmountValue


class WalletOperationResponse(WalletResponse):
    operation_type: str
    amount: int
