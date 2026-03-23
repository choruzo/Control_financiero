import { apiFetchJson, apiFetch } from './client';
import type { AccountResponse, AccountCreate, AccountUpdate } from '$lib/types';

export async function getAccounts(): Promise<AccountResponse[]> {
	return apiFetchJson<AccountResponse[]>('/api/v1/accounts');
}

export async function createAccount(data: AccountCreate): Promise<AccountResponse> {
	return apiFetchJson<AccountResponse>('/api/v1/accounts', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function updateAccount(id: string, data: AccountUpdate): Promise<AccountResponse> {
	return apiFetchJson<AccountResponse>(`/api/v1/accounts/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export async function deleteAccount(id: string): Promise<void> {
	const res = await apiFetch(`/api/v1/accounts/${id}`, { method: 'DELETE' });
	if (!res.ok) throw new Error('Error eliminando cuenta');
}
