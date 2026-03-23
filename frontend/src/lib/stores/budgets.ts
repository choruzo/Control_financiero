import { writable, derived } from 'svelte/store';
import type {
	BudgetStatusResponse,
	BudgetCreate,
	BudgetUpdate,
	CategoryResponse
} from '$lib/types';
import {
	getBudgetStatuses,
	createBudget as apiCreateBudget,
	updateBudget as apiUpdateBudget,
	deleteBudget as apiDeleteBudget
} from '$lib/api/budgets';
import { getCategories } from '$lib/api/categories';

interface BudgetsState {
	statuses: BudgetStatusResponse[];
	/** Últimos 2 meses anteriores al mes actual, más antiguo primero */
	historyStatuses: BudgetStatusResponse[][];
	categories: CategoryResponse[];
	isLoading: boolean;
	error: string | null;
	currentYear: number;
	currentMonth: number;
	lastFetched: number | null;
}

const now = new Date();
const CACHE_TTL_MS = 60_000;

function createBudgetsStore() {
	const { subscribe, set, update } = writable<BudgetsState>({
		statuses: [],
		historyStatuses: [],
		categories: [],
		isLoading: false,
		error: null,
		currentYear: now.getFullYear(),
		currentMonth: now.getMonth() + 1,
		lastFetched: null
	});

	/** Devuelve el mes/año anterior N meses atrás */
	function prevMonth(year: number, month: number, n: number): { year: number; month: number } {
		let m = month - n;
		let y = year;
		while (m <= 0) {
			m += 12;
			y -= 1;
		}
		return { year: y, month: m };
	}

	/**
	 * Carga los statuses del período indicado + 2 meses previos para el gráfico.
	 * Usa caché de 60 s salvo que forceRefresh=true o cambie el período.
	 */
	async function load(year: number, month: number, forceRefresh = false): Promise<void> {
		let currentState: BudgetsState | undefined;
		const unsub = subscribe((s) => (currentState = s));
		unsub();

		const samePeriod =
			currentState?.currentYear === year && currentState?.currentMonth === month;

		if (
			!forceRefresh &&
			samePeriod &&
			currentState?.lastFetched !== null &&
			currentState?.lastFetched !== undefined &&
			Date.now() - currentState.lastFetched < CACHE_TTL_MS
		) {
			return;
		}

		update((s) => ({ ...s, isLoading: true, error: null, currentYear: year, currentMonth: month }));

		const p1 = prevMonth(year, month, 1);
		const p2 = prevMonth(year, month, 2);

		const [statusesResult, hist1Result, hist2Result, categoriesResult] =
			await Promise.allSettled([
				getBudgetStatuses(year, month),
				getBudgetStatuses(p1.year, p1.month),
				getBudgetStatuses(p2.year, p2.month),
				getCategories()
			]);

		if (statusesResult.status === 'rejected') {
			update((s) => ({
				...s,
				isLoading: false,
				error: 'No se pudieron cargar los presupuestos'
			}));
			return;
		}

		update((s) => ({
			...s,
			isLoading: false,
			error: null,
			lastFetched: Date.now(),
			statuses: statusesResult.value,
			historyStatuses: [
				hist2Result.status === 'fulfilled' ? hist2Result.value : [],
				hist1Result.status === 'fulfilled' ? hist1Result.value : []
			],
			categories: categoriesResult.status === 'fulfilled' ? categoriesResult.value : s.categories
		}));
	}

	async function refresh(year: number, month: number): Promise<void> {
		await load(year, month, true);
	}

	async function createBudget(data: BudgetCreate): Promise<void> {
		await apiCreateBudget(data);
		// Recarga el período afectado
		let currentState: BudgetsState | undefined;
		const unsub = subscribe((s) => (currentState = s));
		unsub();
		await load(currentState!.currentYear, currentState!.currentMonth, true);
	}

	async function updateBudget(id: string, data: BudgetUpdate): Promise<void> {
		const updated = await apiUpdateBudget(id, data);
		update((s) => ({
			...s,
			statuses: s.statuses.map((st) =>
				st.budget.id === id ? { ...st, budget: updated } : st
			)
		}));
	}

	async function deleteBudget(id: string): Promise<void> {
		await apiDeleteBudget(id);
		update((s) => ({
			...s,
			statuses: s.statuses.filter((st) => st.budget.id !== id)
		}));
	}

	return { subscribe, load, refresh, createBudget, updateBudget, deleteBudget };
}

export const budgetsStore = createBudgetsStore();
export const budgetsData = derived(budgetsStore, ($s) => $s.statuses);
export const budgetsHistory = derived(budgetsStore, ($s) => $s.historyStatuses);
export const budgetsCategories = derived(budgetsStore, ($s) => $s.categories);
export const budgetsLoading = derived(budgetsStore, ($s) => $s.isLoading);
export const budgetsError = derived(budgetsStore, ($s) => $s.error);
export const budgetsPeriod = derived(budgetsStore, ($s) => ({
	year: $s.currentYear,
	month: $s.currentMonth
}));
