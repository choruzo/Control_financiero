import { writable, derived } from 'svelte/store';
import type { CashflowForecast, ScenarioRequest, ScenarioResponse, MLModelStatus } from '$lib/types';
import { getForecast, analyzeScenario as apiAnalyze, getMLStatus } from '$lib/api/predictions';

interface PredictionsState {
	forecast: CashflowForecast | null;
	scenarioResult: ScenarioResponse | null;
	mlStatus: MLModelStatus | null;
	isLoading: boolean;
	isCalculating: boolean;
	error: string | null;
	lastFetched: number | null;
}

const CACHE_TTL_MS = 60_000;

function createPredictionsStore() {
	const { subscribe, update } = writable<PredictionsState>({
		forecast: null,
		scenarioResult: null,
		mlStatus: null,
		isLoading: false,
		isCalculating: false,
		error: null,
		lastFetched: null
	});

	async function load(forceRefresh = false): Promise<void> {
		let currentState: PredictionsState | undefined;
		const unsub = subscribe((s) => (currentState = s));
		unsub();

		if (
			!forceRefresh &&
			currentState?.lastFetched !== null &&
			currentState?.lastFetched !== undefined &&
			Date.now() - currentState.lastFetched < CACHE_TTL_MS
		) {
			return;
		}

		update((s) => ({ ...s, isLoading: true, error: null }));

		const [forecastResult, mlStatusResult] = await Promise.allSettled([
			getForecast(6),
			getMLStatus()
		]);

		update((s) => ({
			...s,
			isLoading: false,
			lastFetched: Date.now(),
			forecast: forecastResult.status === 'fulfilled' ? forecastResult.value : s.forecast,
			mlStatus: mlStatusResult.status === 'fulfilled' ? mlStatusResult.value : s.mlStatus,
			error:
				forecastResult.status === 'rejected' && mlStatusResult.status === 'rejected'
					? 'No se pudieron cargar las predicciones'
					: null
		}));
	}

	async function analyzeScenario(request: ScenarioRequest): Promise<void> {
		update((s) => ({ ...s, isCalculating: true, error: null }));
		try {
			const result = await apiAnalyze(request);
			update((s) => ({ ...s, isCalculating: false, scenarioResult: result }));
		} catch (err) {
			const msg = err instanceof Error ? err.message : 'Error al analizar el escenario';
			update((s) => ({ ...s, isCalculating: false, error: msg }));
			throw err;
		}
	}

	function clearScenario(): void {
		update((s) => ({ ...s, scenarioResult: null, error: null }));
	}

	return { subscribe, load, analyzeScenario, clearScenario };
}

export const predictionsStore = createPredictionsStore();

export const predictionsLoading = derived(predictionsStore, ($s) => $s.isLoading);
export const predictionsCalculating = derived(predictionsStore, ($s) => $s.isCalculating);
export const predictionsError = derived(predictionsStore, ($s) => $s.error);
export const forecastData = derived(predictionsStore, ($s) => $s.forecast);
export const scenarioData = derived(predictionsStore, ($s) => $s.scenarioResult);
export const mlStatusData = derived(predictionsStore, ($s) => $s.mlStatus);
