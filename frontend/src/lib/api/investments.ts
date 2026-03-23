import { apiFetchJson, apiFetch } from './client';
import type {
	InvestmentResponse,
	InvestmentCreate,
	InvestmentUpdate,
	InvestmentStatusResponse,
	InvestmentSummaryResponse
} from '$lib/types';

export async function getInvestmentSummary(): Promise<InvestmentSummaryResponse> {
	return apiFetchJson<InvestmentSummaryResponse>('/api/v1/investments/summary');
}

export async function getInvestments(filters?: {
	investment_type?: string;
	is_active?: boolean;
}): Promise<InvestmentResponse[]> {
	const params = new URLSearchParams();
	if (filters?.investment_type) params.set('investment_type', filters.investment_type);
	if (filters?.is_active !== undefined) params.set('is_active', String(filters.is_active));
	const qs = params.toString();
	return apiFetchJson<InvestmentResponse[]>(`/api/v1/investments${qs ? '?' + qs : ''}`);
}

export async function getInvestment(id: string): Promise<InvestmentResponse> {
	return apiFetchJson<InvestmentResponse>(`/api/v1/investments/${id}`);
}

export async function getInvestmentStatus(id: string): Promise<InvestmentStatusResponse> {
	return apiFetchJson<InvestmentStatusResponse>(`/api/v1/investments/${id}/status`);
}

export async function createInvestment(data: InvestmentCreate): Promise<InvestmentResponse> {
	return apiFetchJson<InvestmentResponse>('/api/v1/investments', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function updateInvestment(
	id: string,
	data: InvestmentUpdate
): Promise<InvestmentResponse> {
	return apiFetchJson<InvestmentResponse>(`/api/v1/investments/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export async function deleteInvestment(id: string): Promise<void> {
	const res = await apiFetch(`/api/v1/investments/${id}`, { method: 'DELETE' });
	if (!res.ok) throw new Error('Error eliminando inversión');
}

export async function renewInvestment(id: string): Promise<InvestmentResponse> {
	return apiFetchJson<InvestmentResponse>(`/api/v1/investments/${id}/renew`, {
		method: 'POST'
	});
}
