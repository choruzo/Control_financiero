import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetchJson: vi.fn()
}));

const mockForecast = {
	predictions: [
		{
			year: 2026,
			month: 4,
			income_p10: 1800,
			income_p50: 2000,
			income_p90: 2200,
			expenses_p10: 1200,
			expenses_p50: 1400,
			expenses_p90: 1600,
			net_p10: 200,
			net_p50: 600,
			net_p90: 1000
		}
	],
	model_used: 'lstm',
	model_version: '1.0',
	historical_months_used: 12,
	ml_available: true
};

const mockScenarioResponse = {
	name: 'Test',
	parameters: { months_ahead: 6 },
	monthly_results: [],
	summary: {
		period_months: 6,
		total_base_net: 3000,
		total_scenario_net_p50: 4500,
		total_net_improvement: 1500,
		total_net_improvement_p10: 900,
		total_net_improvement_p90: 2100,
		avg_monthly_improvement: 250,
		net_improvement_pct: 50,
		total_tax_impact: null
	},
	mortgage_impact_per_month: null,
	historical_months_used: 12,
	ml_available: true
};

const mockMLStatus = {
	loaded: true,
	version: 'v1.2',
	accuracy: 0.94,
	last_trained: '2026-03-01T03:00:00',
	feedback_count: 3,
	retrain_in_progress: false,
	ml_available: true
};

describe('Predictions API', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('getForecast llama al endpoint correcto con meses por defecto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockForecast);

		const { getForecast } = await import('$lib/api/predictions');
		const result = await getForecast();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/analytics/forecast?months=6');
		expect(result.model_used).toBe('lstm');
		expect(result.predictions).toHaveLength(1);
	});

	it('getForecast acepta número de meses custom', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockForecast);

		const { getForecast } = await import('$lib/api/predictions');
		await getForecast(12);

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/analytics/forecast?months=12');
	});

	it('analyzeScenario hace POST con el body correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockScenarioResponse);

		const { analyzeScenario } = await import('$lib/api/predictions');
		const request = { salary_variation_pct: 10, months_ahead: 6 };
		const result = await analyzeScenario(request);

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/scenarios/analyze',
			expect.objectContaining({ method: 'POST' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.salary_variation_pct).toBe(10);
		expect(body.months_ahead).toBe(6);
		expect(result.summary.total_net_improvement).toBe(1500);
	});

	it('analyzeScenario con gastos recurrentes incluye modifications en el body', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockScenarioResponse);

		const { analyzeScenario } = await import('$lib/api/predictions');
		await analyzeScenario({
			recurring_expense_modifications: [
				{ description: 'Gimnasio', monthly_amount: 50, action: 'add' }
			]
		});

		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.recurring_expense_modifications).toHaveLength(1);
		expect(body.recurring_expense_modifications[0].action).toBe('add');
	});

	it('getMLStatus llama al endpoint correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockMLStatus);

		const { getMLStatus } = await import('$lib/api/predictions');
		const result = await getMLStatus();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/ml/status');
		expect(result.loaded).toBe(true);
		expect(result.accuracy).toBe(0.94);
	});

	it('getForecast propaga errores de la API', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockRejectedValueOnce(new Error('Network error'));

		const { getForecast } = await import('$lib/api/predictions');
		await expect(getForecast()).rejects.toThrow('Network error');
	});

	it('analyzeScenario propaga errores de la API', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockRejectedValueOnce(new Error('Unauthorized'));

		const { analyzeScenario } = await import('$lib/api/predictions');
		await expect(analyzeScenario({ months_ahead: 6 })).rejects.toThrow('Unauthorized');
	});
});
