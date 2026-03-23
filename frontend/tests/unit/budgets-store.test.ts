import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/budgets', () => ({
	getBudgetStatuses: vi.fn(),
	createBudget: vi.fn(),
	updateBudget: vi.fn(),
	deleteBudget: vi.fn()
}));

vi.mock('$lib/api/categories', () => ({
	getCategories: vi.fn()
}));

const mockStatus = (id: string, categoryId: string, spent: number, limit: number) => ({
	budget: {
		id,
		user_id: 'user-1',
		category_id: categoryId,
		period_year: 2026,
		period_month: 3,
		limit_amount: limit,
		alert_threshold: 80,
		name: null,
		created_at: '',
		updated_at: ''
	},
	spent_amount: spent,
	remaining_amount: limit - spent,
	percentage_used: (spent / limit) * 100,
	is_over_limit: spent > limit,
	alert_triggered: (spent / limit) * 100 >= 80
});

const mockStatuses = [
	mockStatus('bud-1', 'cat-1', 200, 500),
	mockStatus('bud-2', 'cat-2', 450, 400)
];

const mockCategories = [
	{ id: 'cat-1', name: 'Alimentación' },
	{ id: 'cat-2', name: 'Transporte' }
];

describe('Budgets Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('load() carga los statuses del mes actual y actualiza el store', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');
		vi.mocked(api.getBudgetStatuses).mockResolvedValue(mockStatuses);
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);

		const { budgetsStore, budgetsData, budgetsLoading, budgetsError } = await import(
			'$lib/stores/budgets'
		);

		await budgetsStore.load(2026, 3);

		expect(get(budgetsLoading)).toBe(false);
		expect(get(budgetsError)).toBeNull();
		expect(get(budgetsData)).toHaveLength(2);
		expect(get(budgetsData)[0].budget.id).toBe('bud-1');
	});

	it('load() también carga los 2 meses anteriores para el historial', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');
		vi.mocked(api.getBudgetStatuses).mockResolvedValue(mockStatuses);
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);

		const { budgetsStore } = await import('$lib/stores/budgets');
		await budgetsStore.load(2026, 3);

		// getBudgetStatuses se llama 3 veces: mes actual + 2 meses anteriores
		expect(api.getBudgetStatuses).toHaveBeenCalledTimes(3);
	});

	it('cache: segunda llamada dentro de 60s no llama a la API de nuevo', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');
		vi.mocked(api.getBudgetStatuses).mockResolvedValue(mockStatuses);
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);

		const { budgetsStore } = await import('$lib/stores/budgets');
		await budgetsStore.load(2026, 3);
		await budgetsStore.load(2026, 3); // segunda llamada — debe usar caché

		expect(api.getBudgetStatuses).toHaveBeenCalledTimes(3); // no aumenta
	});

	it('refresh() fuerza recarga ignorando el caché', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');
		vi.mocked(api.getBudgetStatuses).mockResolvedValue(mockStatuses);
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);

		const { budgetsStore } = await import('$lib/stores/budgets');
		await budgetsStore.load(2026, 3);
		await budgetsStore.refresh(2026, 3);

		// 3 + 3 = 6 llamadas totales
		expect(api.getBudgetStatuses).toHaveBeenCalledTimes(6);
	});

	it('createBudget() llama a la API y recarga los statuses', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');
		vi.mocked(api.getBudgetStatuses).mockResolvedValue(mockStatuses);
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(api.createBudget).mockResolvedValueOnce(mockStatuses[0].budget);

		const { budgetsStore } = await import('$lib/stores/budgets');
		await budgetsStore.load(2026, 3);

		vi.mocked(api.getBudgetStatuses).mockClear();
		await budgetsStore.createBudget({
			category_id: 'cat-3',
			period_year: 2026,
			period_month: 3,
			limit_amount: 300
		});

		expect(api.createBudget).toHaveBeenCalledTimes(1);
		// Recarga forzada tras crear
		expect(api.getBudgetStatuses).toHaveBeenCalled();
	});

	it('deleteBudget() elimina el item del estado', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');
		vi.mocked(api.getBudgetStatuses).mockResolvedValue(mockStatuses);
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(api.deleteBudget).mockResolvedValueOnce(undefined);

		const { budgetsStore, budgetsData } = await import('$lib/stores/budgets');
		await budgetsStore.load(2026, 3);

		expect(get(budgetsData)).toHaveLength(2);
		await budgetsStore.deleteBudget('bud-1');
		expect(get(budgetsData)).toHaveLength(1);
		expect(get(budgetsData)[0].budget.id).toBe('bud-2');
	});

	it('error del historial no bloquea la carga del mes actual', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');

		// Mes actual devuelve datos; los meses previos fallan
		vi.mocked(api.getBudgetStatuses)
			.mockResolvedValueOnce(mockStatuses)   // mes actual
			.mockRejectedValueOnce(new Error('no prev')) // mes-1
			.mockRejectedValueOnce(new Error('no prev')); // mes-2
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);

		const { budgetsStore, budgetsData, budgetsError, budgetsHistory } = await import(
			'$lib/stores/budgets'
		);
		await budgetsStore.load(2026, 3);

		expect(get(budgetsError)).toBeNull();
		expect(get(budgetsData)).toHaveLength(2);
		// Historial con arrays vacíos
		expect(get(budgetsHistory)).toEqual([[], []]);
	});

	it('budgetsLoading es true durante la carga', async () => {
		const api = await import('$lib/api/budgets');
		const catApi = await import('$lib/api/categories');

		let loadingDuringFetch = false;

		vi.mocked(api.getBudgetStatuses).mockImplementation(async () => {
			const { budgetsLoading } = await import('$lib/stores/budgets');
			loadingDuringFetch = get(budgetsLoading);
			return mockStatuses;
		});
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);

		const { budgetsStore } = await import('$lib/stores/budgets');
		await budgetsStore.load(2026, 3);

		expect(loadingDuringFetch).toBe(true);
	});
});
