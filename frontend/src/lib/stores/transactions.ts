import { writable, derived } from 'svelte/store';
import type {
	PaginatedTransactions,
	TransactionItem,
	TransactionCreate,
	TransactionUpdate,
	TransactionFilters,
	AccountResponse,
	CategoryResponse
} from '$lib/types';
import * as txApi from '$lib/api/transactions';
import { getAccounts } from '$lib/api/accounts';
import { getCategories } from '$lib/api/categories';

interface TransactionsState {
	data: PaginatedTransactions | null;
	isLoading: boolean;
	error: string | null;
	filters: TransactionFilters;
	accounts: AccountResponse[];
	categories: CategoryResponse[];
	lastFetched: number | null;
}

const DEFAULT_FILTERS: TransactionFilters = { page: 1, per_page: 50 };
const CACHE_TTL_MS = 60_000;

function createTransactionsStore() {
	const { subscribe, set, update } = writable<TransactionsState>({
		data: null,
		isLoading: false,
		error: null,
		filters: { ...DEFAULT_FILTERS },
		accounts: [],
		categories: [],
		lastFetched: null
	});

	/** Carga transacciones + accounts + categories en paralelo. */
	async function load(forceRefresh = false): Promise<void> {
		let currentState: TransactionsState | undefined;
		const unsub = subscribe((s) => (currentState = s));
		unsub();

		if (
			!forceRefresh &&
			currentState?.lastFetched !== null &&
			currentState?.lastFetched !== undefined &&
			Date.now() - currentState.lastFetched < CACHE_TTL_MS &&
			currentState.data !== null
		) {
			return;
		}

		update((s) => ({ ...s, isLoading: true, error: null }));

		const filters = currentState?.filters ?? DEFAULT_FILTERS;

		const [txResult, accountsResult, categoriesResult] = await Promise.allSettled([
			txApi.getTransactions(filters),
			getAccounts(),
			getCategories()
		]);

		if (txResult.status === 'rejected') {
			update((s) => ({
				...s,
				isLoading: false,
				error: 'No se pudieron cargar las transacciones. Comprueba tu conexión.'
			}));
			return;
		}

		update((s) => ({
			...s,
			isLoading: false,
			error: null,
			lastFetched: Date.now(),
			data: txResult.value,
			accounts: accountsResult.status === 'fulfilled' ? accountsResult.value : s.accounts,
			categories: categoriesResult.status === 'fulfilled' ? categoriesResult.value : s.categories
		}));
	}

	/** Actualiza filtros, resetea a página 1 y recarga. */
	async function setFilters(newFilters: Partial<TransactionFilters>): Promise<void> {
		update((s) => ({
			...s,
			filters: { ...s.filters, ...newFilters, page: 1 },
			lastFetched: null // Invalidar cache
		}));
		await load(true);
	}

	/** Cambia de página y recarga. */
	async function changePage(page: number): Promise<void> {
		update((s) => ({
			...s,
			filters: { ...s.filters, page },
			lastFetched: null
		}));
		await load(true);
	}

	/** Elimina una transacción y recarga la lista. */
	async function deleteTransaction(id: string): Promise<void> {
		await txApi.deleteTransaction(id);
		update((s) => ({ ...s, lastFetched: null }));
		await load(true);
	}

	/** Actualiza la categoría de una transacción.
	 *  Si había una sugerencia ML, envía feedback al modelo. */
	async function updateCategory(
		transaction: TransactionItem,
		newCategoryId: string
	): Promise<TransactionItem> {
		const updated = await txApi.updateTransaction(transaction.id, { category_id: newCategoryId });

		// Enviar feedback ML si había sugerencia pendiente
		if (
			transaction.ml_suggested_category_id &&
			transaction.ml_confidence !== null &&
			transaction.ml_confidence !== undefined
		) {
			txApi
				.sendMlFeedback(
					transaction.id,
					transaction.ml_suggested_category_id,
					newCategoryId,
					transaction.ml_confidence
				)
				.catch(() => {
					// Feedback ML es best-effort, no bloqueamos al usuario si falla
				});
		}

		// Actualizar en estado local
		update((s) => {
			if (!s.data) return s;
			return {
				...s,
				data: {
					...s.data,
					items: s.data.items.map((t) => (t.id === transaction.id ? updated : t))
				}
			};
		});

		return updated;
	}

	/** Agrega una transacción recién creada al estado local. */
	async function addTransaction(data: TransactionCreate): Promise<TransactionItem> {
		const created = await txApi.createTransaction(data);
		update((s) => ({ ...s, lastFetched: null }));
		await load(true);
		return created;
	}

	/** Edita una transacción existente. */
	async function editTransaction(id: string, data: TransactionUpdate): Promise<TransactionItem> {
		const updated = await txApi.updateTransaction(id, data);
		update((s) => {
			if (!s.data) return s;
			return {
				...s,
				data: {
					...s.data,
					items: s.data.items.map((t) => (t.id === id ? updated : t))
				}
			};
		});
		return updated;
	}

	/** Fuerza recarga ignorando el cache. */
	async function refresh(): Promise<void> {
		await load(true);
	}

	return {
		subscribe,
		load,
		setFilters,
		changePage,
		deleteTransaction,
		updateCategory,
		addTransaction,
		editTransaction,
		refresh
	};
}

export const transactionsStore = createTransactionsStore();
export const transactionsData = derived(transactionsStore, ($s) => $s.data);
export const transactionsLoading = derived(transactionsStore, ($s) => $s.isLoading);
export const transactionsError = derived(transactionsStore, ($s) => $s.error);
export const transactionsAccounts = derived(transactionsStore, ($s) => $s.accounts);
export const transactionsCategories = derived(transactionsStore, ($s) => $s.categories);
export const transactionsFilters = derived(transactionsStore, ($s) => $s.filters);
