import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetchJson: vi.fn()
}));

describe('Analytics API', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('getOverview construye la URL correcta', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({});

		const { getOverview } = await import('$lib/api/analytics');
		await getOverview(2026, 3);

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/analytics/overview?year=2026&month=3');
	});

	it('getCashflow construye la URL con el número de meses', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getCashflow } = await import('$lib/api/analytics');
		await getCashflow(12);

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/analytics/cashflow?months=12');
	});

	it('getExpensesByCategory construye la URL correcta', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getExpensesByCategory } = await import('$lib/api/analytics');
		await getExpensesByCategory(2026, 3);

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/analytics/expenses-by-category?year=2026&month=3'
		);
	});

	it('getBudgetAlerts con unreadOnly=true pasa el query param correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getBudgetAlerts } = await import('$lib/api/analytics');
		await getBudgetAlerts(true);

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/budgets/alerts?unread_only=true');
	});

	it('getBudgetAlerts con unreadOnly=false pasa el query param correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getBudgetAlerts } = await import('$lib/api/analytics');
		await getBudgetAlerts(false);

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/budgets/alerts?unread_only=false');
	});

	it('markAlertRead usa PATCH con la ruta correcta', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({});

		const { markAlertRead } = await import('$lib/api/analytics');
		await markAlertRead('alert-uuid-123');

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/budgets/alerts/alert-uuid-123/read',
			{ method: 'PATCH' }
		);
	});

	it('getRecentTransactions construye la URL con paginación correcta', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ items: [], total: 0, page: 1, per_page: 10, pages: 0 });

		const { getRecentTransactions } = await import('$lib/api/analytics');
		await getRecentTransactions(1, 10);

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/transactions?page=1&per_page=10');
	});

	it('getOverview devuelve el valor que retorna apiFetchJson', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		const mockOverview = {
			year: 2026, month: 3,
			total_income: 3000, total_expenses: 2000,
			net_savings: 1000, savings_rate: 33.3,
			total_balance: 10000, transaction_count: 42
		};
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockOverview);

		const { getOverview } = await import('$lib/api/analytics');
		const result = await getOverview(2026, 3);

		expect(result).toEqual(mockOverview);
	});
});
