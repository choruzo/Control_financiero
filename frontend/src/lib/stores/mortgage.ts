import { writable, derived } from 'svelte/store';
import type {
	MortgageSimulateRequest,
	MortgageSimulationResult,
	MortgageCompareRequest,
	MortgageCompareResponse,
	AffordabilityResponse,
	MortgageSaveRequest,
	MortgageSimulationResponse
} from '$lib/types';
import {
	getMortgageSimulations,
	simulateMortgage as apiSimulate,
	compareMortgages as apiCompare,
	getAffordability as apiGetAffordability,
	saveMortgageSimulation as apiSave,
	deleteMortgageSimulation as apiDelete
} from '$lib/api/mortgage';

interface MortgageState {
	simulations: MortgageSimulationResponse[];
	currentResult: MortgageSimulationResult | null;
	comparisonResult: MortgageCompareResponse | null;
	affordabilityData: AffordabilityResponse | null;
	isLoading: boolean;
	isCalculating: boolean;
	error: string | null;
	lastFetched: number | null;
}

const CACHE_TTL_MS = 60_000;

function createMortgageStore() {
	const { subscribe, update } = writable<MortgageState>({
		simulations: [],
		currentResult: null,
		comparisonResult: null,
		affordabilityData: null,
		isLoading: false,
		isCalculating: false,
		error: null,
		lastFetched: null
	});

	async function load(forceRefresh = false): Promise<void> {
		let currentState: MortgageState | undefined;
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

		try {
			const simulations = await getMortgageSimulations();
			update((s) => ({
				...s,
				isLoading: false,
				error: null,
				lastFetched: Date.now(),
				simulations
			}));
		} catch {
			update((s) => ({
				...s,
				isLoading: false,
				error: 'No se pudieron cargar las simulaciones guardadas'
			}));
		}
	}

	async function simulate(data: MortgageSimulateRequest): Promise<void> {
		update((s) => ({ ...s, isCalculating: true, error: null }));
		try {
			const result = await apiSimulate(data);
			update((s) => ({ ...s, isCalculating: false, currentResult: result }));
		} catch (err) {
			const msg = err instanceof Error ? err.message : 'Error al calcular la hipoteca';
			update((s) => ({ ...s, isCalculating: false, error: msg }));
			throw err;
		}
	}

	async function compare(data: MortgageCompareRequest): Promise<void> {
		update((s) => ({ ...s, isCalculating: true, error: null }));
		try {
			const result = await apiCompare(data);
			update((s) => ({ ...s, isCalculating: false, comparisonResult: result }));
		} catch (err) {
			const msg = err instanceof Error ? err.message : 'Error al comparar escenarios';
			update((s) => ({ ...s, isCalculating: false, error: msg }));
			throw err;
		}
	}

	async function loadAffordability(taxConfigId?: string): Promise<void> {
		update((s) => ({ ...s, isCalculating: true, error: null }));
		try {
			const result = await apiGetAffordability(taxConfigId);
			update((s) => ({ ...s, isCalculating: false, affordabilityData: result }));
		} catch (err) {
			const msg = err instanceof Error ? err.message : 'Error al cargar la capacidad hipotecaria';
			update((s) => ({ ...s, isCalculating: false, error: msg }));
			throw err;
		}
	}

	async function saveSimulation(data: MortgageSaveRequest): Promise<void> {
		await apiSave(data);
		await load(true);
	}

	async function deleteSimulation(id: string): Promise<void> {
		update((s) => ({
			...s,
			simulations: s.simulations.filter((sim) => sim.id !== id)
		}));
		try {
			await apiDelete(id);
		} catch {
			// Si falla el DELETE recarga para restaurar estado real
			await load(true);
		}
	}

	function clearResult(): void {
		update((s) => ({ ...s, currentResult: null, comparisonResult: null, error: null }));
	}

	return {
		subscribe,
		load,
		simulate,
		compare,
		loadAffordability,
		saveSimulation,
		deleteSimulation,
		clearResult
	};
}

export const mortgageStore = createMortgageStore();

export const mortgageSimulations = derived(mortgageStore, ($s) => $s.simulations);
export const mortgageCurrentResult = derived(mortgageStore, ($s) => $s.currentResult);
export const mortgageComparison = derived(mortgageStore, ($s) => $s.comparisonResult);
export const mortgageAffordability = derived(mortgageStore, ($s) => $s.affordabilityData);
export const mortgageLoading = derived(mortgageStore, ($s) => $s.isLoading);
export const mortgageCalculating = derived(mortgageStore, ($s) => $s.isCalculating);
export const mortgageError = derived(mortgageStore, ($s) => $s.error);
