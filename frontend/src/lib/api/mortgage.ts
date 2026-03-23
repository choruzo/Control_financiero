import { apiFetchJson, apiFetch } from './client';
import type {
	MortgageSimulateRequest,
	MortgageSimulationResult,
	MortgageCompareRequest,
	MortgageCompareResponse,
	AffordabilityResponse,
	AIAffordabilityResponse,
	MortgageSaveRequest,
	MortgageSimulationResponse
} from '$lib/types';

export async function simulateMortgage(
	data: MortgageSimulateRequest
): Promise<MortgageSimulationResult> {
	return apiFetchJson<MortgageSimulationResult>('/api/v1/mortgage/simulate', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function compareMortgages(
	data: MortgageCompareRequest
): Promise<MortgageCompareResponse> {
	return apiFetchJson<MortgageCompareResponse>('/api/v1/mortgage/compare', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function getAffordability(taxConfigId?: string): Promise<AffordabilityResponse> {
	const params = new URLSearchParams();
	if (taxConfigId) params.set('tax_config_id', taxConfigId);
	const qs = params.toString();
	return apiFetchJson<AffordabilityResponse>(`/api/v1/mortgage/affordability${qs ? '?' + qs : ''}`);
}

export async function getAIAffordability(params?: {
	months_ahead?: number;
	term_years?: number;
	tax_config_id?: string;
	gross_annual?: number;
	euribor_stress_levels?: number[];
}): Promise<AIAffordabilityResponse> {
	const qs = new URLSearchParams();
	if (params?.months_ahead) qs.set('months_ahead', String(params.months_ahead));
	if (params?.term_years) qs.set('term_years', String(params.term_years));
	if (params?.tax_config_id) qs.set('tax_config_id', params.tax_config_id);
	if (params?.gross_annual) qs.set('gross_annual', String(params.gross_annual));
	if (params?.euribor_stress_levels) {
		for (const level of params.euribor_stress_levels) {
			qs.append('euribor_stress_levels', String(level));
		}
	}
	const query = qs.toString();
	return apiFetchJson<AIAffordabilityResponse>(
		`/api/v1/mortgage/ai-affordability${query ? '?' + query : ''}`
	);
}

export async function getMortgageSimulations(): Promise<MortgageSimulationResponse[]> {
	return apiFetchJson<MortgageSimulationResponse[]>('/api/v1/mortgage/simulations');
}

export async function getMortgageSimulation(id: string): Promise<MortgageSimulationResponse> {
	return apiFetchJson<MortgageSimulationResponse>(`/api/v1/mortgage/simulations/${id}`);
}

export async function saveMortgageSimulation(
	data: MortgageSaveRequest
): Promise<MortgageSimulationResponse> {
	return apiFetchJson<MortgageSimulationResponse>('/api/v1/mortgage/simulations', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function deleteMortgageSimulation(id: string): Promise<void> {
	const res = await apiFetch(`/api/v1/mortgage/simulations/${id}`, { method: 'DELETE' });
	if (!res.ok) throw new Error('Error eliminando simulación');
}
