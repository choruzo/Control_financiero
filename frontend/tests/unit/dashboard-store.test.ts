import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/analytics', () => ({
	getOverview: vi.fn(),
	getCashflow: vi.fn(),
	getExpensesByCategory: vi.fn(),
	getBudgetAlerts: vi.fn(),
	markAlertRead: vi.fn(),
	getRecentTransactions: vi.fn()
}));

const mockOverview = {
	year: 2026, month: 3,
	total_income: 3000, total_expenses: 2000,
	net_savings: 1000, savings_rate: 33.3,
	total_balance: 10000, transaction_count: 42
};

const mockCashflow = [{ year: 2026, month: 3, total_income: 3000, total_expenses: 2000, net: 1000 }];
const mockCategories = [{ category_id: 'cat-1', category_name: 'Alimentación', total_amount: 500, transaction_count: 10, percentage: 25 }];
const mockAlerts = [{ id: 'alert-1', budget_id: 'budget-1', triggered_at: '2026-03-01T00:00:00Z', spent_amount: 900, percentage: 90, is_read: false }];
const mockTransactions = { items: [{ id: 'tx-1', account_id: 'acc-1', amount: 50, description: 'Mercadona', transaction_type: 'expense', date: '2026-03-20', category_id: 'cat-1', is_recurring: false, ml_suggested_category_id: null, ml_confidence: null }], total: 1, page: 1, per_page: 10, pages: 1 };

describe('Dashboard Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('load() carga todos los datos y actualiza el store', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockResolvedValueOnce(mockOverview);
		vi.mocked(api.getCashflow).mockResolvedValueOnce(mockCashflow);
		vi.mocked(api.getExpensesByCategory).mockResolvedValueOnce(mockCategories);
		vi.mocked(api.getBudgetAlerts).mockResolvedValueOnce(mockAlerts);
		vi.mocked(api.getRecentTransactions).mockResolvedValueOnce(mockTransactions);

		const { dashboardStore, dashboardData, dashboardLoading, dashboardError } = await import('$lib/stores/dashboard');

		await dashboardStore.load(2026, 3);

		expect(get(dashboardLoading)).toBe(false);
		expect(get(dashboardError)).toBeNull();
		const data = get(dashboardData);
		expect(data).not.toBeNull();
		expect(data?.overview).toEqual(mockOverview);
		expect(data?.cashflow).toEqual(mockCashflow);
		expect(data?.expensesByCategory).toEqual(mockCategories);
		expect(data?.budgetAlerts).toEqual(mockAlerts);
		expect(data?.recentTransactions).toHaveLength(1);
	});

	it('cuando overview falla establece error y data=null', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockRejectedValueOnce(new Error('500'));
		vi.mocked(api.getCashflow).mockResolvedValueOnce([]);
		vi.mocked(api.getExpensesByCategory).mockResolvedValueOnce([]);
		vi.mocked(api.getBudgetAlerts).mockResolvedValueOnce([]);
		vi.mocked(api.getRecentTransactions).mockResolvedValueOnce({ items: [], total: 0, page: 1, per_page: 10, pages: 0 });

		const { dashboardStore, dashboardData, dashboardError } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);

		expect(get(dashboardError)).not.toBeNull();
		expect(get(dashboardData)).toBeNull();
	});

	it('cuando budgetAlerts falla devuelve array vacío en lugar de fallar', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockResolvedValueOnce(mockOverview);
		vi.mocked(api.getCashflow).mockResolvedValueOnce(mockCashflow);
		vi.mocked(api.getExpensesByCategory).mockResolvedValueOnce(mockCategories);
		vi.mocked(api.getBudgetAlerts).mockRejectedValueOnce(new Error('No budgets'));
		vi.mocked(api.getRecentTransactions).mockResolvedValueOnce(mockTransactions);

		const { dashboardStore, dashboardData, dashboardError } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);

		expect(get(dashboardError)).toBeNull();
		expect(get(dashboardData)?.budgetAlerts).toEqual([]);
	});

	it('cuando recentTransactions falla devuelve array vacío', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockResolvedValueOnce(mockOverview);
		vi.mocked(api.getCashflow).mockResolvedValueOnce([]);
		vi.mocked(api.getExpensesByCategory).mockResolvedValueOnce([]);
		vi.mocked(api.getBudgetAlerts).mockResolvedValueOnce([]);
		vi.mocked(api.getRecentTransactions).mockRejectedValueOnce(new Error('No transactions'));

		const { dashboardStore, dashboardData } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);

		expect(get(dashboardData)?.recentTransactions).toEqual([]);
	});

	it('cache: segunda llamada dentro de 60s no llama a la API de nuevo', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockResolvedValue(mockOverview);
		vi.mocked(api.getCashflow).mockResolvedValue(mockCashflow);
		vi.mocked(api.getExpensesByCategory).mockResolvedValue(mockCategories);
		vi.mocked(api.getBudgetAlerts).mockResolvedValue(mockAlerts);
		vi.mocked(api.getRecentTransactions).mockResolvedValue(mockTransactions);

		const { dashboardStore } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);
		await dashboardStore.load(2026, 3); // segunda llamada — debe usar cache

		expect(api.getOverview).toHaveBeenCalledTimes(1);
	});

	it('refresh() fuerza recarga ignorando el cache', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockResolvedValue(mockOverview);
		vi.mocked(api.getCashflow).mockResolvedValue(mockCashflow);
		vi.mocked(api.getExpensesByCategory).mockResolvedValue(mockCategories);
		vi.mocked(api.getBudgetAlerts).mockResolvedValue(mockAlerts);
		vi.mocked(api.getRecentTransactions).mockResolvedValue(mockTransactions);

		const { dashboardStore } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);
		await dashboardStore.refresh(2026, 3); // fuerza recarga

		expect(api.getOverview).toHaveBeenCalledTimes(2);
	});

	it('markAlertRead elimina la alerta del estado local', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockResolvedValueOnce(mockOverview);
		vi.mocked(api.getCashflow).mockResolvedValueOnce(mockCashflow);
		vi.mocked(api.getExpensesByCategory).mockResolvedValueOnce(mockCategories);
		vi.mocked(api.getBudgetAlerts).mockResolvedValueOnce(mockAlerts);
		vi.mocked(api.getRecentTransactions).mockResolvedValueOnce(mockTransactions);
		vi.mocked(api.markAlertRead).mockResolvedValueOnce({ ...mockAlerts[0], is_read: true });

		const { dashboardStore, dashboardData } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);

		expect(get(dashboardData)?.budgetAlerts).toHaveLength(1);

		await dashboardStore.markAlertRead('alert-1');

		expect(get(dashboardData)?.budgetAlerts).toHaveLength(0);
	});

	it('markAlertRead llama a api.markAlertRead con el id correcto', async () => {
		const api = await import('$lib/api/analytics');
		vi.mocked(api.getOverview).mockResolvedValueOnce(mockOverview);
		vi.mocked(api.getCashflow).mockResolvedValueOnce([]);
		vi.mocked(api.getExpensesByCategory).mockResolvedValueOnce([]);
		vi.mocked(api.getBudgetAlerts).mockResolvedValueOnce(mockAlerts);
		vi.mocked(api.getRecentTransactions).mockResolvedValueOnce(mockTransactions);
		vi.mocked(api.markAlertRead).mockResolvedValueOnce({ ...mockAlerts[0], is_read: true });

		const { dashboardStore } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);
		await dashboardStore.markAlertRead('alert-1');

		expect(api.markAlertRead).toHaveBeenCalledWith('alert-1');
	});

	it('dashboardLoading es true durante la carga', async () => {
		const api = await import('$lib/api/analytics');
		let loadingDuringFetch = false;

		vi.mocked(api.getOverview).mockImplementationOnce(async () => {
			// Capturar estado de loading durante la llamada
			const { dashboardLoading } = await import('$lib/stores/dashboard');
			loadingDuringFetch = get(dashboardLoading);
			return mockOverview;
		});
		vi.mocked(api.getCashflow).mockResolvedValueOnce([]);
		vi.mocked(api.getExpensesByCategory).mockResolvedValueOnce([]);
		vi.mocked(api.getBudgetAlerts).mockResolvedValueOnce([]);
		vi.mocked(api.getRecentTransactions).mockResolvedValueOnce({ items: [], total: 0, page: 1, per_page: 10, pages: 0 });

		const { dashboardStore } = await import('$lib/stores/dashboard');
		await dashboardStore.load(2026, 3);

		expect(loadingDuringFetch).toBe(true);
	});
});
