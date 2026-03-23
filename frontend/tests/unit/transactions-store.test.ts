import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/transactions', () => ({
	getTransactions: vi.fn(),
	createTransaction: vi.fn(),
	updateTransaction: vi.fn(),
	deleteTransaction: vi.fn(),
	sendMlFeedback: vi.fn()
}));

vi.mock('$lib/api/accounts', () => ({
	getAccounts: vi.fn()
}));

vi.mock('$lib/api/categories', () => ({
	getCategories: vi.fn()
}));

const mockPaginated = {
	items: [
		{
			id: 'tx-1',
			account_id: 'acc-1',
			amount: 50,
			description: 'Mercadona',
			transaction_type: 'expense',
			date: '2026-03-20',
			category_id: 'cat-1',
			is_recurring: false,
			ml_suggested_category_id: null,
			ml_confidence: null
		}
	],
	total: 1,
	page: 1,
	per_page: 50,
	pages: 1
};

const mockAccounts = [{ id: 'acc-1', name: 'N26', bank: 'N26', account_type: 'checking', currency: 'EUR', balance: 1000, is_active: true, user_id: 'u-1', created_at: '', updated_at: '' }];
const mockCategories = [{ id: 'cat-1', name: 'Alimentación', user_id: null, parent_id: null, color: null, icon: null, is_system: true, created_at: '', updated_at: '' }];

describe('Transactions Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('load() carga transacciones, accounts y categories en paralelo', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValueOnce(mockPaginated);
		vi.mocked(accsApi.getAccounts).mockResolvedValueOnce(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValueOnce(mockCategories);

		const { transactionsStore, transactionsData, transactionsAccounts, transactionsCategories } =
			await import('$lib/stores/transactions');

		await transactionsStore.load();

		expect(get(transactionsData)).not.toBeNull();
		expect(get(transactionsData)?.items).toHaveLength(1);
		expect(get(transactionsAccounts)).toHaveLength(1);
		expect(get(transactionsCategories)).toHaveLength(1);
	});

	it('cuando getTransactions falla, establece error y data=null', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockRejectedValueOnce(new Error('500'));
		vi.mocked(accsApi.getAccounts).mockResolvedValueOnce([]);
		vi.mocked(catsApi.getCategories).mockResolvedValueOnce([]);

		const { transactionsStore, transactionsData, transactionsError } =
			await import('$lib/stores/transactions');

		await transactionsStore.load();

		expect(get(transactionsError)).not.toBeNull();
		expect(get(transactionsData)).toBeNull();
	});

	it('setFilters resetea la página a 1 y recarga', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValue(mockPaginated);
		vi.mocked(accsApi.getAccounts).mockResolvedValue(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValue(mockCategories);

		const { transactionsStore, transactionsFilters } = await import('$lib/stores/transactions');

		// Simular que estamos en página 3
		await transactionsStore.changePage(3);

		// Aplicar filtros → debe resetear a página 1
		await transactionsStore.setFilters({ transaction_type: 'expense' });

		expect(get(transactionsFilters).page).toBe(1);
		expect(get(transactionsFilters).transaction_type).toBe('expense');
	});

	it('changePage actualiza el filtro de página y recarga', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValue(mockPaginated);
		vi.mocked(accsApi.getAccounts).mockResolvedValue(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValue(mockCategories);

		const { transactionsStore, transactionsFilters } = await import('$lib/stores/transactions');

		await transactionsStore.changePage(2);

		expect(get(transactionsFilters).page).toBe(2);
		expect(txApi.getTransactions).toHaveBeenCalled();
	});

	it('deleteTransaction llama a la API y recarga', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValue(mockPaginated);
		vi.mocked(txApi.deleteTransaction).mockResolvedValueOnce(undefined);
		vi.mocked(accsApi.getAccounts).mockResolvedValue(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValue(mockCategories);

		const { transactionsStore } = await import('$lib/stores/transactions');

		await transactionsStore.deleteTransaction('tx-1');

		expect(txApi.deleteTransaction).toHaveBeenCalledWith('tx-1');
		// Debe recargar después de eliminar
		expect(txApi.getTransactions).toHaveBeenCalled();
	});

	it('updateCategory hace PATCH y envía feedback ML si había sugerencia', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValue(mockPaginated);
		vi.mocked(accsApi.getAccounts).mockResolvedValue(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValue(mockCategories);

		const transactionWithMl = {
			...mockPaginated.items[0],
			ml_suggested_category_id: 'suggested-cat',
			ml_confidence: 0.75
		};
		vi.mocked(txApi.updateTransaction).mockResolvedValueOnce(transactionWithMl);
		vi.mocked(txApi.sendMlFeedback).mockResolvedValueOnce(undefined);

		const { transactionsStore } = await import('$lib/stores/transactions');
		await transactionsStore.load();

		await transactionsStore.updateCategory(transactionWithMl, 'new-cat-uuid');

		expect(txApi.updateTransaction).toHaveBeenCalledWith(
			transactionWithMl.id,
			expect.objectContaining({ category_id: 'new-cat-uuid' })
		);
		// Esperar un tick para que el feedback async se procese
		await new Promise((r) => setTimeout(r, 0));
		expect(txApi.sendMlFeedback).toHaveBeenCalledWith(
			transactionWithMl.id,
			'suggested-cat',
			'new-cat-uuid',
			0.75
		);
	});

	it('updateCategory no envía feedback ML si no había sugerencia', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValue(mockPaginated);
		vi.mocked(accsApi.getAccounts).mockResolvedValue(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValue(mockCategories);
		vi.mocked(txApi.updateTransaction).mockResolvedValueOnce(mockPaginated.items[0]);

		const { transactionsStore } = await import('$lib/stores/transactions');
		await transactionsStore.load();

		// Transacción sin sugerencia ML
		await transactionsStore.updateCategory(mockPaginated.items[0], 'cat-2');

		await new Promise((r) => setTimeout(r, 0));
		expect(txApi.sendMlFeedback).not.toHaveBeenCalled();
	});

	it('cache: segunda llamada dentro de 60s no llama a la API de nuevo', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValue(mockPaginated);
		vi.mocked(accsApi.getAccounts).mockResolvedValue(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValue(mockCategories);

		const { transactionsStore } = await import('$lib/stores/transactions');
		await transactionsStore.load();
		await transactionsStore.load(); // segunda llamada — debe usar cache

		expect(txApi.getTransactions).toHaveBeenCalledTimes(1);
	});

	it('refresh() fuerza recarga ignorando el cache', async () => {
		const txApi = await import('$lib/api/transactions');
		const accsApi = await import('$lib/api/accounts');
		const catsApi = await import('$lib/api/categories');
		vi.mocked(txApi.getTransactions).mockResolvedValue(mockPaginated);
		vi.mocked(accsApi.getAccounts).mockResolvedValue(mockAccounts);
		vi.mocked(catsApi.getCategories).mockResolvedValue(mockCategories);

		const { transactionsStore } = await import('$lib/stores/transactions');
		await transactionsStore.load();
		await transactionsStore.refresh();

		expect(txApi.getTransactions).toHaveBeenCalledTimes(2);
	});
});
