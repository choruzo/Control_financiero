import { writable, derived } from 'svelte/store';
import type {
	CategoryResponse,
	CategoryCreate,
	CategoryUpdate,
	TaxBracketResponse,
	TaxConfigCreate,
	TaxConfigUpdate,
	TaxConfigResponse
} from '$lib/types';
import { getCategories, createCategory as apiCreateCategory, updateCategory as apiUpdateCategory, deleteCategory as apiDeleteCategory } from '$lib/api/categories';
import {
	getTaxConfigs,
	getTaxBrackets,
	createTaxConfig as apiCreateTaxConfig,
	updateTaxConfig as apiUpdateTaxConfig,
	deleteTaxConfig as apiDeleteTaxConfig
} from '$lib/api/tax';

interface SettingsState {
	categories: CategoryResponse[];
	taxConfigs: TaxConfigResponse[];
	taxBrackets: TaxBracketResponse[];
	isLoading: boolean;
	error: string | null;
	lastFetched: number | null;
}

const CACHE_TTL_MS = 60_000;

function createSettingsStore() {
	const { subscribe, update } = writable<SettingsState>({
		categories: [],
		taxConfigs: [],
		taxBrackets: [],
		isLoading: false,
		error: null,
		lastFetched: null
	});

	async function load(forceRefresh = false): Promise<void> {
		let currentState: SettingsState | undefined;
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

		const [categoriesResult, taxConfigsResult, taxBracketsResult] = await Promise.allSettled([
			getCategories(),
			getTaxConfigs(),
			getTaxBrackets(2025)
		]);

		if (categoriesResult.status === 'rejected') {
			update((s) => ({
				...s,
				isLoading: false,
				error: 'No se pudieron cargar las categorías'
			}));
			return;
		}

		update((s) => ({
			...s,
			isLoading: false,
			error: null,
			lastFetched: Date.now(),
			categories: categoriesResult.value,
			taxConfigs: taxConfigsResult.status === 'fulfilled' ? taxConfigsResult.value : s.taxConfigs,
			taxBrackets:
				taxBracketsResult.status === 'fulfilled' ? taxBracketsResult.value : s.taxBrackets
		}));
	}

	async function createCategory(data: CategoryCreate): Promise<void> {
		await apiCreateCategory(data);
		await load(true);
	}

	async function updateCategory(id: string, data: CategoryUpdate): Promise<void> {
		const updated = await apiUpdateCategory(id, data);
		update((s) => ({
			...s,
			categories: s.categories.map((c) => (c.id === id ? updated : c))
		}));
	}

	async function deleteCategory(id: string): Promise<void> {
		update((s) => ({
			...s,
			categories: s.categories.filter((c) => c.id !== id)
		}));
		try {
			await apiDeleteCategory(id);
		} catch {
			await load(true);
		}
	}

	async function createTaxConfig(data: TaxConfigCreate): Promise<void> {
		await apiCreateTaxConfig(data);
		await load(true);
	}

	async function updateTaxConfig(id: string, data: TaxConfigUpdate): Promise<void> {
		const updated = await apiUpdateTaxConfig(id, data);
		update((s) => ({
			...s,
			taxConfigs: s.taxConfigs.map((c) => (c.id === id ? updated : c))
		}));
	}

	async function deleteTaxConfig(id: string): Promise<void> {
		update((s) => ({
			...s,
			taxConfigs: s.taxConfigs.filter((c) => c.id !== id)
		}));
		try {
			await apiDeleteTaxConfig(id);
		} catch {
			await load(true);
		}
	}

	return {
		subscribe,
		load,
		createCategory,
		updateCategory,
		deleteCategory,
		createTaxConfig,
		updateTaxConfig,
		deleteTaxConfig
	};
}

export const settingsStore = createSettingsStore();

export const settingsCategories = derived(settingsStore, ($s) => $s.categories);
export const settingsCustomCategories = derived(settingsStore, ($s) =>
	$s.categories.filter((c) => !c.is_system)
);
export const settingsSystemCategories = derived(settingsStore, ($s) =>
	$s.categories.filter((c) => c.is_system)
);
export const settingsTaxConfigs = derived(settingsStore, ($s) => $s.taxConfigs);
export const settingsTaxBrackets = derived(settingsStore, ($s) => $s.taxBrackets);
export const settingsLoading = derived(settingsStore, ($s) => $s.isLoading);
export const settingsError = derived(settingsStore, ($s) => $s.error);
