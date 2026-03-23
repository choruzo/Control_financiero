import { apiFetchJson, apiFetch } from './client';
import type {
	TaxBracketResponse,
	TaxConfigCreate,
	TaxConfigUpdate,
	TaxConfigResponse,
	TaxCalculationResponse
} from '$lib/types';

export async function getTaxBrackets(
	year?: number,
	bracketType?: 'general' | 'savings'
): Promise<TaxBracketResponse[]> {
	const params = new URLSearchParams();
	if (year !== undefined) params.set('year', String(year));
	if (bracketType) params.set('bracket_type', bracketType);
	const qs = params.toString();
	return apiFetchJson<TaxBracketResponse[]>(`/api/v1/tax/brackets${qs ? '?' + qs : ''}`);
}

export async function getTaxConfigs(): Promise<TaxConfigResponse[]> {
	return apiFetchJson<TaxConfigResponse[]>('/api/v1/tax/configs');
}

export async function createTaxConfig(data: TaxConfigCreate): Promise<TaxConfigResponse> {
	return apiFetchJson<TaxConfigResponse>('/api/v1/tax/configs', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function updateTaxConfig(
	id: string,
	data: TaxConfigUpdate
): Promise<TaxConfigResponse> {
	return apiFetchJson<TaxConfigResponse>(`/api/v1/tax/configs/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export async function deleteTaxConfig(id: string): Promise<void> {
	const res = await apiFetch(`/api/v1/tax/configs/${id}`, { method: 'DELETE' });
	if (!res.ok) throw new Error('Error eliminando configuración fiscal');
}

export async function getTaxCalculation(id: string): Promise<TaxCalculationResponse> {
	return apiFetchJson<TaxCalculationResponse>(`/api/v1/tax/configs/${id}/calculation`);
}
