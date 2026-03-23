import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetchJson: vi.fn(),
	apiFetch: vi.fn()
}));

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

const mockSavedSim = {
	id: 'sim-1',
	name: 'Piso centro',
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
};

describe('Mortgage API', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('simulateMortgage hace POST al endpoint correcto con body', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockSimResult);

		const { simulateMortgage } = await import('$lib/api/mortgage');
		const result = await simulateMortgage({
			property_price: 300000,
			down_payment: 60000,
			rate_type: 'fixed',
			term_years: 30,
			interest_rate: 3.5
		});

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/mortgage/simulate',
			expect.objectContaining({ method: 'POST' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.property_price).toBe(300000);
		expect(body.rate_type).toBe('fixed');
		expect(result.initial_monthly_payment).toBe(1077.71);
	});

	it('compareMortgages hace POST con la lista de escenarios', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({
			loan_amount: 240000,
			term_years: 30,
			scenarios: []
		});

		const { compareMortgages } = await import('$lib/api/mortgage');
		await compareMortgages({
			property_price: 300000,
			down_payment: 60000,
			term_years: 30,
			scenarios: [
				{ name: 'Fijo', rate_type: 'fixed', interest_rate: 3.5 },
				{ name: 'Variable', rate_type: 'variable', euribor_rate: 3.5, spread: 0.8 }
			]
		});

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/mortgage/compare',
			expect.objectContaining({ method: 'POST' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.scenarios).toHaveLength(2);
	});

	it('getAffordability sin taxConfigId llama sin query params', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({
			monthly_net_income: 3000,
			max_monthly_payment: 1050,
			recommended_max_loan: 200000,
			options: []
		});

		const { getAffordability } = await import('$lib/api/mortgage');
		await getAffordability();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/mortgage/affordability');
	});

	it('getAffordability con taxConfigId incluye el query param', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({
			monthly_net_income: 2800,
			max_monthly_payment: 980,
			recommended_max_loan: 180000,
			options: []
		});

		const { getAffordability } = await import('$lib/api/mortgage');
		await getAffordability('tax-config-uuid');

		const url = vi.mocked(apiFetchJson).mock.calls[0][0] as string;
		expect(url).toContain('tax_config_id=tax-config-uuid');
	});

	it('getMortgageSimulations llama al endpoint de listado', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([mockSavedSim]);

		const { getMortgageSimulations } = await import('$lib/api/mortgage');
		const result = await getMortgageSimulations();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/mortgage/simulations');
		expect(result).toHaveLength(1);
	});

	it('saveMortgageSimulation hace POST con nombre en el body', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockSavedSim);

		const { saveMortgageSimulation } = await import('$lib/api/mortgage');
		const result = await saveMortgageSimulation({
			name: 'Piso centro',
			property_price: 300000,
			down_payment: 60000,
			rate_type: 'fixed',
			term_years: 30,
			interest_rate: 3.5
		});

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/mortgage/simulations',
			expect.objectContaining({ method: 'POST' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.name).toBe('Piso centro');
		expect(result.id).toBe('sim-1');
	});

	it('deleteMortgageSimulation hace DELETE al endpoint con el ID', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true } as Response);

		const { deleteMortgageSimulation } = await import('$lib/api/mortgage');
		await expect(deleteMortgageSimulation('sim-1')).resolves.toBeUndefined();

		expect(apiFetch).toHaveBeenCalledWith('/api/v1/mortgage/simulations/sim-1', { method: 'DELETE' });
	});

	it('deleteMortgageSimulation lanza error si response no es ok', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: false, status: 404 } as Response);

		const { deleteMortgageSimulation } = await import('$lib/api/mortgage');
		await expect(deleteMortgageSimulation('no-existe')).rejects.toThrow('Error eliminando simulación');
	});
});
