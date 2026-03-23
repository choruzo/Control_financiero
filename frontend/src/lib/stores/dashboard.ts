import { writable, derived } from 'svelte/store';
import type { DashboardData } from '$lib/types';
import * as api from '$lib/api/analytics';

interface DashboardState {
	data: DashboardData | null;
	isLoading: boolean;
	error: string | null;
	lastFetched: number | null;
}

const CACHE_TTL_MS = 60_000;

function createDashboardStore() {
	const { subscribe, set, update } = writable<DashboardState>({
		data: null,
		isLoading: false,
		error: null,
		lastFetched: null
	});

	/** Carga en paralelo todos los datos del dashboard con tolerancia a fallos parciales. */
	async function load(year: number, month: number, forceRefresh = false): Promise<void> {
		let currentState: DashboardState | undefined;
		// Leer estado actual sin suscripción
		const unsub = subscribe((s) => (currentState = s));
		unsub();

		// Cache: no recargar si los datos son recientes
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

		const [overviewResult, cashflowResult, categoryResult, alertsResult, transactionsResult] =
			await Promise.allSettled([
				api.getOverview(year, month),
				api.getCashflow(12),
				api.getExpensesByCategory(year, month),
				api.getBudgetAlerts(true),
				api.getRecentTransactions(1, 10)
			]);

		// overview es crítico: si falla, el dashboard no puede mostrarse
		if (overviewResult.status === 'rejected') {
			update((s) => ({
				...s,
				isLoading: false,
				error: 'No se pudieron cargar los datos del dashboard. Comprueba tu conexión.'
			}));
			return;
		}

		set({
			isLoading: false,
			error: null,
			lastFetched: Date.now(),
			data: {
				overview: overviewResult.value,
				cashflow: cashflowResult.status === 'fulfilled' ? cashflowResult.value : [],
				expensesByCategory: categoryResult.status === 'fulfilled' ? categoryResult.value : [],
				budgetAlerts: alertsResult.status === 'fulfilled' ? alertsResult.value : [],
				recentTransactions:
					transactionsResult.status === 'fulfilled' ? transactionsResult.value.items : []
			}
		});
	}

	/** Marca una alerta como leída de forma optimista y llama a la API. */
	async function markAlertRead(alertId: string): Promise<void> {
		// Actualización optimista: eliminar del estado local inmediatamente
		update((s) => {
			if (!s.data) return s;
			return {
				...s,
				data: {
					...s.data,
					budgetAlerts: s.data.budgetAlerts.filter((a) => a.id !== alertId)
				}
			};
		});

		try {
			await api.markAlertRead(alertId);
		} catch {
			// Si falla, volvemos a recargar las alertas en la próxima llamada (no revertir optimista)
		}
	}

	/** Fuerza recarga ignorando el cache. */
	async function refresh(year: number, month: number): Promise<void> {
		await load(year, month, true);
	}

	return { subscribe, load, markAlertRead, refresh };
}

export const dashboardStore = createDashboardStore();
export const dashboardData = derived(dashboardStore, ($s) => $s.data);
export const dashboardLoading = derived(dashboardStore, ($s) => $s.isLoading);
export const dashboardError = derived(dashboardStore, ($s) => $s.error);
