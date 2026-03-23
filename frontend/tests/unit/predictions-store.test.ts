import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/predictions', () => ({
	getForecast: vi.fn(),
	analyzeScenario: vi.fn(),
	getMLStatus: vi.fn()
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

const mockMLStatus = {
	loaded: true,
	version: 'v1.2',
	accuracy: 0.94,
	last_trained: '2026-03-01T03:00:00',
	feedback_count: 3,
	retrain_in_progress: false,
	ml_available: true
};

const mockScenarioResponse = {
	name: 'Escenario test',
	parameters: { months_ahead: 6, salary_variation_pct: 10 },
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

describe('Predictions Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('estado inicial es correcto', async () => {
		const { predictionsStore, predictionsLoading, predictionsError, forecastData, mlStatusData } =
			await import('$lib/stores/predictions');

		expect(get(predictionsLoading)).toBe(false);
		expect(get(predictionsError)).toBeNull();
		expect(get(forecastData)).toBeNull();
		expect(get(mlStatusData)).toBeNull();
	});

	it('load() carga forecast y mlStatus en paralelo', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockResolvedValue(mockForecast);
		vi.mocked(api.getMLStatus).mockResolvedValue(mockMLStatus);

		const { predictionsStore, forecastData, mlStatusData, predictionsLoading } =
			await import('$lib/stores/predictions');

		await predictionsStore.load();

		expect(get(predictionsLoading)).toBe(false);
		expect(get(forecastData)?.model_used).toBe('lstm');
		expect(get(mlStatusData)?.loaded).toBe(true);
		expect(api.getForecast).toHaveBeenCalledTimes(1);
		expect(api.getMLStatus).toHaveBeenCalledTimes(1);
	});

	it('cache: segunda llamada dentro de 60s no llama a la API de nuevo', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockResolvedValue(mockForecast);
		vi.mocked(api.getMLStatus).mockResolvedValue(mockMLStatus);

		const { predictionsStore } = await import('$lib/stores/predictions');
		await predictionsStore.load();
		await predictionsStore.load();

		expect(api.getForecast).toHaveBeenCalledTimes(1);
	});

	it('forceRefresh=true ignora la caché y recarga', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockResolvedValue(mockForecast);
		vi.mocked(api.getMLStatus).mockResolvedValue(mockMLStatus);

		const { predictionsStore } = await import('$lib/stores/predictions');
		await predictionsStore.load();
		await predictionsStore.load(true);

		expect(api.getForecast).toHaveBeenCalledTimes(2);
	});

	it('analyzeScenario actualiza scenarioResult y limpia isCalculating', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockResolvedValue(mockForecast);
		vi.mocked(api.getMLStatus).mockResolvedValue(mockMLStatus);
		vi.mocked(api.analyzeScenario).mockResolvedValue(mockScenarioResponse);

		const { predictionsStore, scenarioData, predictionsCalculating } =
			await import('$lib/stores/predictions');

		await predictionsStore.load();
		await predictionsStore.analyzeScenario({ salary_variation_pct: 10, months_ahead: 6 });

		expect(get(predictionsCalculating)).toBe(false);
		expect(get(scenarioData)?.name).toBe('Escenario test');
		expect(get(scenarioData)?.summary.total_net_improvement).toBe(1500);
	});

	it('clearScenario limpia scenarioResult', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockResolvedValue(mockForecast);
		vi.mocked(api.getMLStatus).mockResolvedValue(mockMLStatus);
		vi.mocked(api.analyzeScenario).mockResolvedValue(mockScenarioResponse);

		const { predictionsStore, scenarioData } = await import('$lib/stores/predictions');

		await predictionsStore.load();
		await predictionsStore.analyzeScenario({ months_ahead: 6 });
		expect(get(scenarioData)).not.toBeNull();

		predictionsStore.clearScenario();
		expect(get(scenarioData)).toBeNull();
	});

	it('degradación parcial: mlStatus falla pero forecast se carga', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockResolvedValue(mockForecast);
		vi.mocked(api.getMLStatus).mockRejectedValueOnce(new Error('ML offline'));

		const { predictionsStore, forecastData, mlStatusData, predictionsError } =
			await import('$lib/stores/predictions');

		await predictionsStore.load();

		expect(get(predictionsError)).toBeNull();
		expect(get(forecastData)?.model_used).toBe('lstm');
		expect(get(mlStatusData)).toBeNull();
	});

	it('error total cuando ambas llamadas fallan', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockRejectedValueOnce(new Error('error'));
		vi.mocked(api.getMLStatus).mockRejectedValueOnce(new Error('error'));

		const { predictionsStore, predictionsError } = await import('$lib/stores/predictions');

		await predictionsStore.load();

		expect(get(predictionsError)).toBe('No se pudieron cargar las predicciones');
	});

	it('analyzeScenario propaga error y actualiza predictionsError', async () => {
		const api = await import('$lib/api/predictions');
		vi.mocked(api.getForecast).mockResolvedValue(mockForecast);
		vi.mocked(api.getMLStatus).mockResolvedValue(mockMLStatus);
		vi.mocked(api.analyzeScenario).mockRejectedValueOnce(new Error('Backend error'));

		const { predictionsStore, predictionsCalculating } = await import('$lib/stores/predictions');

		await predictionsStore.load();
		await expect(predictionsStore.analyzeScenario({})).rejects.toThrow('Backend error');
		expect(get(predictionsCalculating)).toBe(false);
	});
});
