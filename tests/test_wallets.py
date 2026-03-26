from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.core.constants import POSTGRES_BIGINT_MAX


@pytest.mark.asyncio
async def test_get_wallet_balance_success(client, wallet_factory):
    wallet = await wallet_factory(balance=1000)

    response = await client.get(f"/api/v1/wallets/{wallet.id}")

    assert response.status_code == 200
    assert response.json() == {
        "wallet_id": str(wallet.id),
        "balance": 1000,
    }


@pytest.mark.asyncio
async def test_get_wallet_balance_not_found(client):
    response = await client.get(f"/api/v1/wallets/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Wallet not found"}


@pytest.mark.asyncio
async def test_deposit_success(client, wallet_factory):
    wallet = await wallet_factory(balance=1000)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "DEPOSIT", "amount": 500},
    )

    assert response.status_code == 200
    assert response.json() == {
        "wallet_id": str(wallet.id),
        "balance": 1500,
        "operation_type": "DEPOSIT",
        "amount": 500,
    }


@pytest.mark.asyncio
async def test_withdraw_success(client, wallet_factory):
    wallet = await wallet_factory(balance=1000)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "WITHDRAW", "amount": 400},
    )

    assert response.status_code == 200
    assert response.json() == {
        "wallet_id": str(wallet.id),
        "balance": 600,
        "operation_type": "WITHDRAW",
        "amount": 400,
    }


@pytest.mark.asyncio
async def test_withdraw_insufficient_funds(client, wallet_factory):
    wallet = await wallet_factory(balance=100)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "WITHDRAW", "amount": 200},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Insufficient funds"}


@pytest.mark.asyncio
async def test_operation_for_missing_wallet(client):
    response = await client.post(
        f"/api/v1/wallets/{uuid4()}/operation",
        json={"operation_type": "DEPOSIT", "amount": 100},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Wallet not found"}


@pytest.mark.asyncio
async def test_invalid_operation_type_returns_400(client, wallet_factory):
    wallet = await wallet_factory(balance=100)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "TRANSFER", "amount": 100},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid operation type"}


@pytest.mark.asyncio
async def test_invalid_amount_type_returns_422(client, wallet_factory):
    wallet = await wallet_factory(balance=100)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "DEPOSIT", "amount": "abc"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_zero_amount_returns_400(client, wallet_factory):
    wallet = await wallet_factory(balance=100)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "DEPOSIT", "amount": 0},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Amount must be greater than zero"}


@pytest.mark.asyncio
async def test_negative_amount_returns_400(client, wallet_factory):
    wallet = await wallet_factory(balance=100)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "DEPOSIT", "amount": -10},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Amount must be greater than zero"}


@pytest.mark.asyncio
async def test_too_large_amount_returns_422(client, wallet_factory):
    wallet = await wallet_factory(balance=100)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "DEPOSIT", "amount": POSTGRES_BIGINT_MAX + 1},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_deposit_overflow_returns_409(client, wallet_factory):
    wallet = await wallet_factory(balance=POSTGRES_BIGINT_MAX - 5)

    response = await client.post(
        f"/api/v1/wallets/{wallet.id}/operation",
        json={"operation_type": "DEPOSIT", "amount": 10},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Balance limit exceeded"}


@pytest.mark.asyncio
async def test_parallel_deposits_are_not_lost(client, wallet_factory):
    wallet = await wallet_factory(balance=0)

    async def make_deposit():
        return await client.post(
            f"/api/v1/wallets/{wallet.id}/operation",
            json={"operation_type": "DEPOSIT", "amount": 10},
        )

    responses = await asyncio.gather(*[make_deposit() for _ in range(20)])
    balance_response = await client.get(f"/api/v1/wallets/{wallet.id}")

    assert all(response.status_code == 200 for response in responses)
    assert balance_response.json()["balance"] == 200


@pytest.mark.asyncio
async def test_parallel_withdrawals_reject_excess_operations(client, wallet_factory):
    wallet = await wallet_factory(balance=100)

    async def make_withdraw():
        return await client.post(
            f"/api/v1/wallets/{wallet.id}/operation",
            json={"operation_type": "WITHDRAW", "amount": 15},
        )

    responses = await asyncio.gather(*[make_withdraw() for _ in range(10)])
    success_count = sum(response.status_code == 200 for response in responses)
    conflict_count = sum(response.status_code == 409 for response in responses)
    balance_response = await client.get(f"/api/v1/wallets/{wallet.id}")

    assert success_count == 6
    assert conflict_count == 4
    assert balance_response.json()["balance"] == 10


@pytest.mark.asyncio
async def test_parallel_mixed_operations_keep_consistent_balance(client, wallet_factory):
    wallet = await wallet_factory(balance=200)

    async def make_deposit():
        return await client.post(
            f"/api/v1/wallets/{wallet.id}/operation",
            json={"operation_type": "DEPOSIT", "amount": 10},
        )

    async def make_withdraw():
        return await client.post(
            f"/api/v1/wallets/{wallet.id}/operation",
            json={"operation_type": "WITHDRAW", "amount": 15},
        )

    responses = await asyncio.gather(
        *[make_deposit() for _ in range(5)],
        *[make_withdraw() for _ in range(10)],
    )
    balance_response = await client.get(f"/api/v1/wallets/{wallet.id}")

    assert all(response.status_code == 200 for response in responses)
    assert balance_response.json()["balance"] == 100
