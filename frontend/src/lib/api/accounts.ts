import { apiFetchJson } from './client';
import type { AccountResponse } from '$lib/types';

export async function getAccounts(): Promise<AccountResponse[]> {
	return apiFetchJson<AccountResponse[]>('/api/v1/accounts');
}
