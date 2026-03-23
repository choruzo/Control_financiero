import { apiFetch, apiFetchJson } from './client';
import type {
	PaginatedTransactions,
	TransactionItem,
	TransactionCreate,
	TransactionUpdate,
	TransactionFilters,
	ImportResult
} from '$lib/types';

export async function getTransactions(
	filters: TransactionFilters = {}
): Promise<PaginatedTransactions> {
	const params = new URLSearchParams();
	if (filters.date_from) params.set('date_from', filters.date_from);
	if (filters.date_to) params.set('date_to', filters.date_to);
	if (filters.category_id) params.set('category_id', filters.category_id);
	if (filters.account_id) params.set('account_id', filters.account_id);
	if (filters.transaction_type) params.set('transaction_type', filters.transaction_type);
	if (filters.page) params.set('page', String(filters.page));
	if (filters.per_page) params.set('per_page', String(filters.per_page));

	const query = params.toString();
	return apiFetchJson<PaginatedTransactions>(`/api/v1/transactions${query ? '?' + query : ''}`);
}

export async function createTransaction(data: TransactionCreate): Promise<TransactionItem> {
	return apiFetchJson<TransactionItem>('/api/v1/transactions', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function updateTransaction(
	id: string,
	data: TransactionUpdate
): Promise<TransactionItem> {
	return apiFetchJson<TransactionItem>(`/api/v1/transactions/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export async function deleteTransaction(id: string): Promise<void> {
	const response = await apiFetch(`/api/v1/transactions/${id}`, { method: 'DELETE' });
	if (!response.ok) {
		throw new Error('Error al eliminar la transacción');
	}
}

export async function importCsv(
	file: File,
	accountId: string,
	dryRun: boolean
): Promise<ImportResult> {
	const params = new URLSearchParams({ account_id: accountId, dry_run: String(dryRun) });
	const formData = new FormData();
	formData.append('file', file);

	return apiFetchJson<ImportResult>(
		`/api/v1/transactions/import/csv?${params.toString()}`,
		{ method: 'POST', body: formData }
	);
}

export async function sendMlFeedback(
	transactionId: string,
	originalCategoryId: string,
	correctCategoryId: string,
	confidence: number
): Promise<void> {
	await apiFetchJson('/api/v1/ml/feedback', {
		method: 'POST',
		body: JSON.stringify({
			transaction_id: transactionId,
			original_category_id: originalCategoryId,
			correct_category_id: correctCategoryId,
			confidence
		})
	});
}
