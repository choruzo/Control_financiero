import { apiFetchJson } from './client';
import type {
	OverviewData,
	CashflowMonth,
	CategoryExpense,
	BudgetAlertResponse,
	PaginatedTransactions
} from '$lib/types';

export async function getOverview(year: number, month: number): Promise<OverviewData> {
	return apiFetchJson<OverviewData>(
		`/api/v1/analytics/overview?year=${year}&month=${month}`
	);
}

export async function getCashflow(months: number): Promise<CashflowMonth[]> {
	return apiFetchJson<CashflowMonth[]>(
		`/api/v1/analytics/cashflow?months=${months}`
	);
}

export async function getExpensesByCategory(
	year: number,
	month: number
): Promise<CategoryExpense[]> {
	return apiFetchJson<CategoryExpense[]>(
		`/api/v1/analytics/expenses-by-category?year=${year}&month=${month}`
	);
}

export async function getBudgetAlerts(unreadOnly: boolean): Promise<BudgetAlertResponse[]> {
	return apiFetchJson<BudgetAlertResponse[]>(
		`/api/v1/budgets/alerts?unread_only=${unreadOnly}`
	);
}

export async function markAlertRead(alertId: string): Promise<BudgetAlertResponse> {
	return apiFetchJson<BudgetAlertResponse>(
		`/api/v1/budgets/alerts/${alertId}/read`,
		{ method: 'PATCH' }
	);
}

export async function getRecentTransactions(
	page: number,
	perPage: number
): Promise<PaginatedTransactions> {
	return apiFetchJson<PaginatedTransactions>(
		`/api/v1/transactions?page=${page}&per_page=${perPage}`
	);
}
