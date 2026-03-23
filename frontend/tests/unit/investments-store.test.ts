import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/investments', () => ({
	getInvestments: vi.fn(),
	getInvestmentSummary: vi.fn(),
	createInvestment: vi.fn(),
	updateInvestment: vi.fn(),
	deleteInvestment: vi.fn(),
	renewInvestment: vi.fn()
}));

const makeInvestment = (id: string, type = 'deposit', maturityDate: string | null = null) => ({
	id,
	user_id: 'user-1',
	account_id: null,
	name: `Inversión ${id}`,
	investment_type: type,
	principal_amount: 10000,
	interest_rate: 4.25,
	interest_type: 'simple',
	compounding_frequency: null,
	current_value: null,
	start_date: '2025-01-01',
	maturity_date: maturityDate,
	auto_renew: false,
	renewal_period_months: null,
	renewals_count: 0,
	notes: null,
	is_active: true,
	created_at: '',
	updated_at: ''
});

const mockSummary = {
	total_investments: 2,
	total_principal: 20000,
	total_current_value: 20850,
	total_return: 850,
	average_return_percentage: 4.25,
	by_type: { deposit: 2 }
};

const mockInvestments = [
	makeInvestment('inv-1', 'deposit'),
	makeInvestment('inv-2', 'fund')
];

describe('Investments Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('load() carga inversiones y summary y actualiza el store', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockResolvedValue(mockSummary);

		const { investmentsStore, investmentsData, investmentsSummary, investmentsLoading, investmentsError } =
			await import('$lib/stores/investments');

		await investmentsStore.load();

		expect(get(investmentsLoading)).toBe(false);
		expect(get(investmentsError)).toBeNull();
		expect(get(investmentsData)).toHaveLength(2);
		expect(get(investmentsSummary)?.total_investments).toBe(2);
	});

	it('cache: segunda llamada dentro de 60s no llama a la API de nuevo', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockResolvedValue(mockSummary);

		const { investmentsStore } = await import('$lib/stores/investments');
		await investmentsStore.load();
		await investmentsStore.load(); // segunda — debe usar caché

		expect(api.getInvestments).toHaveBeenCalledTimes(1);
	});

	it('forceRefresh=true ignora la caché y recarga', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockResolvedValue(mockSummary);

		const { investmentsStore } = await import('$lib/stores/investments');
		await investmentsStore.load();
		await investmentsStore.load(true);

		expect(api.getInvestments).toHaveBeenCalledTimes(2);
	});

	it('createInvestment llama a la API y recarga', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockResolvedValue(mockSummary);
		vi.mocked(api.createInvestment).mockResolvedValueOnce(makeInvestment('inv-3') as never);

		const { investmentsStore } = await import('$lib/stores/investments');
		await investmentsStore.load();
		vi.mocked(api.getInvestments).mockClear();

		await investmentsStore.createInvestment({
			name: 'Nueva inversión',
			investment_type: 'deposit',
			principal_amount: 5000,
			interest_rate: 3.5,
			interest_type: 'simple',
			start_date: '2026-01-01'
		});

		expect(api.createInvestment).toHaveBeenCalledTimes(1);
		expect(api.getInvestments).toHaveBeenCalled(); // forzó recarga
	});

	it('updateInvestment actualiza optimistamente el item en el store', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockResolvedValue(mockSummary);
		const updated = { ...makeInvestment('inv-1', 'deposit'), interest_rate: 5.0 };
		vi.mocked(api.updateInvestment).mockResolvedValueOnce(updated as never);

		const { investmentsStore, investmentsData } = await import('$lib/stores/investments');
		await investmentsStore.load();
		await investmentsStore.updateInvestment('inv-1', { interest_rate: 5.0 });

		const inv = get(investmentsData).find((i) => i.id === 'inv-1');
		expect(inv?.interest_rate).toBe(5.0);
	});

	it('deleteInvestment elimina el item del estado', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockResolvedValue(mockSummary);
		vi.mocked(api.deleteInvestment).mockResolvedValueOnce(undefined);

		const { investmentsStore, investmentsData } = await import('$lib/stores/investments');
		await investmentsStore.load();

		expect(get(investmentsData)).toHaveLength(2);
		await investmentsStore.deleteInvestment('inv-1');
		expect(get(investmentsData)).toHaveLength(1);
		expect(get(investmentsData)[0].id).toBe('inv-2');
	});

	it('renewInvestment llama a la API y recarga', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockResolvedValue(mockSummary);
		const renewed = { ...makeInvestment('inv-1', 'deposit'), renewals_count: 1 };
		vi.mocked(api.renewInvestment).mockResolvedValueOnce(renewed as never);

		const { investmentsStore } = await import('$lib/stores/investments');
		await investmentsStore.load();
		vi.mocked(api.getInvestments).mockClear();

		await investmentsStore.renewInvestment('inv-1');

		expect(api.renewInvestment).toHaveBeenCalledWith('inv-1');
		expect(api.getInvestments).toHaveBeenCalled(); // recarga tras renovar
	});

	it('degradación parcial: summary falla pero inversiones se cargan', async () => {
		const api = await import('$lib/api/investments');
		vi.mocked(api.getInvestments).mockResolvedValue(mockInvestments as never);
		vi.mocked(api.getInvestmentSummary).mockRejectedValueOnce(new Error('summary error'));

		const { investmentsStore, investmentsData, investmentsSummary, investmentsError } =
			await import('$lib/stores/investments');
		await investmentsStore.load();

		expect(get(investmentsError)).toBeNull();
		expect(get(investmentsData)).toHaveLength(2);
		expect(get(investmentsSummary)).toBeNull(); // summary no cargó
	});
});
