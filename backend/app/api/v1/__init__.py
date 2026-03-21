from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    analytics,
    auth,
    budgets,
    categories,
    investments,
    mortgage,
    tax,
    transactions,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(accounts.router)
router.include_router(categories.router)
router.include_router(transactions.router)
router.include_router(budgets.router)
router.include_router(investments.router)
router.include_router(analytics.router)
router.include_router(mortgage.router)
router.include_router(tax.router)
