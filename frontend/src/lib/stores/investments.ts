import { writable, derived } from 'svelte/store';
import type {
	InvestmentResponse,
	InvestmentCreate,
	InvestmentUpdate,
	InvestmentSummaryResponse
} from '$lib/types';
import {
	getInvestments,
	getInvestmentSummary,
	createInvestment as apiCreate,
	updateInvestment as apiUpdate,
	deleteInvestment as apiDelete,
	renewInvestment as apiRenew
} from '$lib/api/investments';

interface InvestmentsState {
	investments: InvestmentResponse[];
	summary: InvestmentSummaryResponse | null;
	isLoading: boolean;
	error: string | null;
	lastFetched: number | null;
	typeFilter: string | null;
}

const CACHE_TTL_MS = 60_000;

function createInvestmentsStore() {
	const { subscribe, update } = writable<InvestmentsState>({
		investments: [],
		summary: null,
		isLoading: false,
		error: null,
		lastFetched: null,
		typeFilter: null
	});

	async function load(forceRefresh = false): Promise<void> {
		let currentState: InvestmentsState | undefined;
		const unsub = subscribe((s) => (currentState = s));
		unsub();

		if (
			!forceRefresh &&
			currentState?.lastFetched !== null &&
			currentState?.lastFetched !== undefined &&
			Date.now() - currentState.lastFetched < CACHE_TTL_MS
		) {
			return;
		}

		update((s) => ({ ...s, isLoading: true, error: null }));

		const [investmentsResult, summaryResult] = await Promise.allSettled([
			getInvestments({ is_active: true }),
			getInvestmentSummary()
		]);

		if (investmentsResult.status === 'rejected') {
			update((s) => ({
				...s,
				isLoading: false,
				error: 'No se pudieron cargar las inversiones'
			}));
			return;
		}

		update((s) => ({
			...s,
			isLoading: false,
			error: null,
			lastFetched: Date.now(),
			investments: investmentsResult.value,
			summary: summaryResult.status === 'fulfilled' ? summaryResult.value : s.summary
		}));
	}

	function setTypeFilter(type: string | null): void {
		update((s) => ({ ...s, typeFilter: type, lastFetched: null }));
		load(true);
	}

	async function createInvestment(data: InvestmentCreate): Promise<void> {
		await apiCreate(data);
		await load(true);
	}

	async function updateInvestment(id: string, data: InvestmentUpdate): Promise<void> {
		const updated = await apiUpdate(id, data);
		update((s) => ({
			...s,
			investments: s.investments.map((inv) => (inv.id === id ? updated : inv))
		}));
		// Recarga el summary porque el rendimiento puede haber cambiado
		try {
			const summary = await getInvestmentSummary();
			update((s) => ({ ...s, summary }));
		} catch {
			// best-effort
		}
	}

	async function deleteInvestment(id: string): Promise<void> {
		await apiDelete(id);
		update((s) => ({
			...s,
			investments: s.investments.filter((inv) => inv.id !== id)
		}));
		try {
			const summary = await getInvestmentSummary();
			update((s) => ({ ...s, summary }));
		} catch {
			// best-effort
		}
	}

	async function renewInvestment(id: string): Promise<void> {
		await apiRenew(id);
		await load(true);
	}

	return { subscribe, load, setTypeFilter, createInvestment, updateInvestment, deleteInvestment, renewInvestment };
}

export const investmentsStore = createInvestmentsStore();

export const investmentsData = derived(investmentsStore, ($s) => {
	if (!$s.typeFilter) return $s.investments;
	return $s.investments.filter((inv) => inv.investment_type === $s.typeFilter);
});

export const investmentsSummary = derived(investmentsStore, ($s) => $s.summary);
export const investmentsLoading = derived(investmentsStore, ($s) => $s.isLoading);
export const investmentsError = derived(investmentsStore, ($s) => $s.error);
export const investmentsTypeFilter = derived(investmentsStore, ($s) => $s.typeFilter);

export const investmentsMaturingSoon = derived(investmentsStore, ($s) => {
	const today = new Date();
	const soon = new Date(today);
	soon.setDate(today.getDate() + 30);
	return $s.investments.filter((inv) => {
		if (!inv.maturity_date) return false;
		const maturity = new Date(inv.maturity_date);
		return maturity >= today && maturity <= soon;
	});
});
