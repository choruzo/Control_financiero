import { apiFetchJson } from './client';
import type { CashflowForecast, ScenarioRequest, ScenarioResponse, MLModelStatus } from '$lib/types';

export async function getForecast(months = 6): Promise<CashflowForecast> {
	return apiFetchJson<CashflowForecast>(`/api/v1/analytics/forecast?months=${months}`);
}

export async function analyzeScenario(request: ScenarioRequest): Promise<ScenarioResponse> {
	return apiFetchJson<ScenarioResponse>('/api/v1/scenarios/analyze', {
		method: 'POST',
		body: JSON.stringify(request)
	});
}

export async function getMLStatus(): Promise<MLModelStatus> {
	return apiFetchJson<MLModelStatus>('/api/v1/ml/status');
}
