"""A small Transactions API - the thing we load test.

It keeps everything in memory (no database) so it is easy to start anywhere.
Two environment variables let you SIMULATE a performance problem on purpose,
which proves that the load test's pass/fail gate really works:

    SLOW_MS=800   -> every request takes 800 ms longer
    FAIL_RATE=0.2 -> 20% of requests fail with HTTP 500
"""
import asyncio
import os
import random
import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Transactions API", version="1.0")

TRANSACTIONS: dict[str, dict] = {}   # transaction id -> transaction
SLOW_MS = int(os.getenv("SLOW_MS", "0"))
FAIL_RATE = float(os.getenv("FAIL_RATE", "0"))


class TransactionIn(BaseModel):
    account_id: str = Field(pattern=r"^ACC-\d{4}$", examples=["ACC-0001"])
    amount: float = Field(gt=0, examples=[125.50])
    currency: Literal["PLN", "EUR", "USD"]


async def simulate_work():
    """Pretend to talk to a database: a few milliseconds of latency, plus optional trouble."""
    await asyncio.sleep(random.uniform(0.005, 0.03) + SLOW_MS / 1000)
    if FAIL_RATE and random.random() < FAIL_RATE:
        raise HTTPException(status_code=500, detail="Simulated failure")


@app.get("/health")
async def health():
    return {"status": "ok", "transactions": len(TRANSACTIONS)}


@app.post("/transactions", status_code=201)
async def create_transaction(body: TransactionIn):
    await simulate_work()
    transaction = {"id": str(uuid.uuid4()), **body.model_dump()}
    TRANSACTIONS[transaction["id"]] = transaction
    return transaction


@app.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    await simulate_work()
    if transaction_id not in TRANSACTIONS:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TRANSACTIONS[transaction_id]


@app.get("/transactions")
async def list_transactions(account_id: str, limit: int = 20):
    await simulate_work()
    matches = [t for t in TRANSACTIONS.values() if t["account_id"] == account_id]
    return {"account_id": account_id, "count": len(matches), "items": matches[-limit:]}


@app.get("/accounts/{account_id}/balance")
async def balance(account_id: str):
    await simulate_work()
    total = sum(t["amount"] for t in TRANSACTIONS.values() if t["account_id"] == account_id)
    return {"account_id": account_id, "balance": round(total, 2)}
