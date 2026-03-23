import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/mortgage', () => ({
	getMortgageSimulations: vi.fn(),
	simulateMortgage: vi.fn(),
	compareMortgages: vi.fn(),
	getAffordability: vi.fn(),
	saveMortgageSimulation: vi.fn(),
	deleteMortgageSimulation: vi.fn()
}));

const makeSim = (id: string) => ({
	id,
	name: `Simulación ${id}`,
	property_price: 300000,
	down_payment: 60000,
	loan_amount: 240000,
	rate_type: 'fixed',
	term_years: 30,
	interest_rate: 3.5,
	euribor_rate: null,
	spread: null,
	fixed_years: null,
	review_frequency: null,
	property_type: 'second_hand',
	region_tax_rate: null,
	initial_monthly_payment: 1077.71,
	total_amount_paid: 387975.6,
	total_interest: 147975.6,
	created_at: '2026-01-01T00:00:00Z'
});

const mockSimResult = {
	loan_amount: 240000,
	rate_type: 'fixed',
	term_years: 30,
	initial_monthly_payment: 1077.71,
	total_amount_paid: 387975.6,
	total_interest: 147975.6,
	effective_annual_rate: 3.5,
	schedule: [],
	closing_costs: null
};

const mockAffordability = {
	monthly_net_income: 3000,
	max_monthly_payment: 1050,
	recommended_max_loan: 200000,
	options: []
};

describe('Mortgage Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('estado inicial es correcto', async () => {
		const api = await import('$lib/api/mortgage');
		vi.mocked(api.getMortgageSimulations).mockResolvedValue([]);

		const { mortgageStore, mortgageSimulations, mortgageCurrentResult, mortgageLoading, mortgageError } =
			await import('$lib/stores/mortgage');

		expect(get(mortgageLoading)).toBe(false);
		expect(get(mortgageError)).toBeNull();
		expect(get(mortgageCurrentResult)).toBeNull();
		expect(get(mortgageSimulations)).toHaveLength(0);
	});

	it('load() carga las simulaciones guardadas', async () => {
		const api = await import('$lib/api/mortgage');
		vi.mocked(api.getMortgageSimulations).mockResolvedValue([makeSim('sim-1'), makeSim('sim-2')]);

		const { mortgageStore, mortgageSimulations, mortgageLoading, mortgageError } =
			await import('$lib/stores/mortgage');
		await mortgageStore.load();

		expect(get(mortgageLoading)).toBe(false);
		expect(get(mortgageError)).toBeNull();
		expect(get(mortgageSimulations)).toHaveLength(2);
	});

	it('cache TTL: segunda llamada dentro de 60s no llama a la API de nuevo', async () => {
		const api = await import('$lib/api/mortgage');
		vi.mocked(api.getMortgageSimulations).mockResolvedValue([makeSim('sim-1')]);

		const { mortgageStore } = await import('$lib/stores/mortgage');
		await mortgageStore.load();
		await mortgageStore.load(); // usa caché

		expect(api.getMortgageSimulations).toHaveBeenCalledTimes(1);
	});

	it('simulate() actualiza currentResult', async () => {
		const api = await import('$lib/api/mortgage');
		vi.mocked(api.simulateMortgage).mockResolvedValueOnce(mockSimResult as never);

		const { mortgageStore, mortgageCurrentResult } = await import('$lib/stores/mortgage');
		await mortgageStore.simulate({
			property_price: 300000,
			down_payment: 60000,
			rate_type: 'fixed',
			term_years: 30,
			interest_rate: 3.5
		});

		const result = get(mortgageCurrentResult);
		expect(result?.initial_monthly_payment).toBe(1077.71);
		expect(result?.rate_type).toBe('fixed');
	});

	it('compare() actualiza comparisonResult', async () => {
		const api = await import('$lib/api/mortgage');
		const mockCompare = { loan_amount: 240000, term_years: 30, scenarios: [{ name: 'Fijo', rate_type: 'fixed', initial_monthly_payment: 1077, total_amount_paid: 387000, total_interest: 147000, savings_vs_first: null }] };
		vi.mocked(api.compareMortgages).mockResolvedValueOnce(mockCompare as never);

		const { mortgageStore, mortgageComparison } = await import('$lib/stores/mortgage');
		await mortgageStore.compare({
			property_price: 300000,
			down_payment: 60000,
			term_years: 30,
			scenarios: [{ name: 'Fijo', rate_type: 'fixed', interest_rate: 3.5 }]
		});

		const comp = get(mortgageComparison);
		expect(comp?.scenarios).toHaveLength(1);
		expect(comp?.loan_amount).toBe(240000);
	});

	it('loadAffordability() actualiza affordabilityData', async () => {
		const api = await import('$lib/api/mortgage');
		vi.mocked(api.getAffordability).mockResolvedValueOnce(mockAffordability as never);

		const { mortgageStore, mortgageAffordability } = await import('$lib/stores/mortgage');
		await mortgageStore.loadAffordability();

		const data = get(mortgageAffordability);
		expect(data?.monthly_net_income).toBe(3000);
		expect(data?.max_monthly_payment).toBe(1050);
	});

	it('saveSimulation() llama a la API y recarga la lista', async () => {
		const api = await import('$lib/api/mortgage');
		vi.mocked(api.getMortgageSimulations).mockResolvedValue([makeSim('sim-1')]);
		vi.mocked(api.saveMortgageSimulation).mockResolvedValueOnce(makeSim('sim-2') as never);

		const { mortgageStore } = await import('$lib/stores/mortgage');
		await mortgageStore.saveSimulation({
			name: 'Mi hipoteca',
			property_price: 300000,
			down_payment: 60000,
			rate_type: 'fixed',
			term_years: 30,
			interest_rate: 3.5
		});

		expect(api.saveMortgageSimulation).toHaveBeenCalledTimes(1);
		expect(api.getMortgageSimulations).toHaveBeenCalled();
	});

	it('deleteSimulation() elimina el item del estado optimistamente', async () => {
		const api = await import('$lib/api/mortgage');
		vi.mocked(api.getMortgageSimulations).mockResolvedValue([makeSim('sim-1'), makeSim('sim-2')]);
		vi.mocked(api.deleteMortgageSimulation).mockResolvedValueOnce(undefined);

		const { mortgageStore, mortgageSimulations } = await import('$lib/stores/mortgage');
		await mortgageStore.load();

		expect(get(mortgageSimulations)).toHaveLength(2);
		await mortgageStore.deleteSimulation('sim-1');

		expect(get(mortgageSimulations)).toHaveLength(1);
		expect(get(mortgageSimulations)[0].id).toBe('sim-2');
	});
});
