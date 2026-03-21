from fastapi import APIRouter

from app.api.v1 import accounts, auth, budgets, categories, investments, transactions

router = APIRouter()
router.include_router(auth.router)
router.include_router(accounts.router)
router.include_router(categories.router)
router.include_router(transactions.router)
router.include_router(budgets.router)
router.include_router(investments.router)
