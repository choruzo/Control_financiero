import { apiFetchJson, apiFetch } from './client';
import type {
	BudgetResponse,
	BudgetCreate,
	BudgetUpdate,
	BudgetStatusResponse,
	BudgetAlertResponse
} from '$lib/types';

export async function getBudgets(year?: number, month?: number): Promise<BudgetResponse[]> {
	const params = new URLSearchParams();
	if (year !== undefined) params.set('period_year', String(year));
	if (month !== undefined) params.set('period_month', String(month));
	const qs = params.toString();
	return apiFetchJson<BudgetResponse[]>(`/api/v1/budgets${qs ? '?' + qs : ''}`);
}

export async function createBudget(data: BudgetCreate): Promise<BudgetResponse> {
	return apiFetchJson<BudgetResponse>('/api/v1/budgets', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function updateBudget(id: string, data: BudgetUpdate): Promise<BudgetResponse> {
	return apiFetchJson<BudgetResponse>(`/api/v1/budgets/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export async function deleteBudget(id: string): Promise<void> {
	const res = await apiFetch(`/api/v1/budgets/${id}`, { method: 'DELETE' });
	if (!res.ok) throw new Error('Error eliminando presupuesto');
}

export async function getBudgetStatuses(
	year: number,
	month: number
): Promise<BudgetStatusResponse[]> {
	return apiFetchJson<BudgetStatusResponse[]>(
		`/api/v1/budgets/status?period_year=${year}&period_month=${month}`
	);
}

export async function getBudgetAlerts(unreadOnly = false): Promise<BudgetAlertResponse[]> {
	return apiFetchJson<BudgetAlertResponse[]>(
		`/api/v1/budgets/alerts${unreadOnly ? '?unread_only=true' : ''}`
	);
}

export async function markBudgetAlertRead(alertId: string): Promise<BudgetAlertResponse> {
	return apiFetchJson<BudgetAlertResponse>(`/api/v1/budgets/alerts/${alertId}/read`, {
		method: 'PATCH'
	});
}
