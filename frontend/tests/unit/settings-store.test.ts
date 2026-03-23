import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$lib/api/categories', () => ({
	getCategories: vi.fn(),
	createCategory: vi.fn(),
	updateCategory: vi.fn(),
	deleteCategory: vi.fn()
}));

vi.mock('$lib/api/tax', () => ({
	getTaxConfigs: vi.fn(),
	getTaxBrackets: vi.fn(),
	createTaxConfig: vi.fn(),
	updateTaxConfig: vi.fn(),
	deleteTaxConfig: vi.fn()
}));

const makeCategory = (id: string, isSystem = false) => ({
	id,
	user_id: isSystem ? null : 'user-1',
	parent_id: null,
	name: `Categoría ${id}`,
	color: '#6366f1',
	icon: '🏷️',
	is_system: isSystem,
	created_at: '',
	updated_at: ''
});

const mockCategories = [
	makeCategory('cat-sys-1', true),
	makeCategory('cat-sys-2', true),
	makeCategory('cat-custom-1', false)
];

const mockTaxConfigs = [
	{ id: 'cfg-1', tax_year: 2025, gross_annual_salary: 35000, created_at: '', updated_at: '' }
];

const mockBrackets = [
	{ id: 'br-1', tax_year: 2025, bracket_type: 'general', min_amount: 0, max_amount: 12450, rate: 0.19 }
];

describe('Settings Store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('estado inicial es vacío y no cargando', async () => {
		const {
			settingsStore,
			settingsCategories,
			settingsTaxConfigs,
			settingsLoading,
			settingsError
		} = await import('$lib/stores/settings');

		expect(get(settingsCategories)).toEqual([]);
		expect(get(settingsTaxConfigs)).toEqual([]);
		expect(get(settingsLoading)).toBe(false);
		expect(get(settingsError)).toBeNull();
	});

	it('load() carga categorías y taxConfigs en paralelo', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(taxApi.getTaxConfigs).mockResolvedValue(mockTaxConfigs as never);
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue(mockBrackets as never);

		const { settingsStore, settingsCategories, settingsTaxConfigs, settingsLoading } =
			await import('$lib/stores/settings');

		await settingsStore.load();

		expect(get(settingsLoading)).toBe(false);
		expect(get(settingsCategories)).toHaveLength(3);
		expect(get(settingsTaxConfigs)).toHaveLength(1);
	});

	it('caché TTL: segunda llamada dentro de 60s no recarga', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(taxApi.getTaxConfigs).mockResolvedValue(mockTaxConfigs as never);
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue(mockBrackets as never);

		const { settingsStore } = await import('$lib/stores/settings');
		await settingsStore.load();
		await settingsStore.load();

		expect(catApi.getCategories).toHaveBeenCalledTimes(1);
	});

	it('degradación parcial: taxConfigs falla pero categorías se cargan', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(taxApi.getTaxConfigs).mockRejectedValueOnce(new Error('tax error'));
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue([]);

		const { settingsStore, settingsCategories, settingsTaxConfigs, settingsError } =
			await import('$lib/stores/settings');

		await settingsStore.load();

		expect(get(settingsError)).toBeNull();
		expect(get(settingsCategories)).toHaveLength(3);
		expect(get(settingsTaxConfigs)).toEqual([]);
	});

	it('createCategory llama a la API y fuerza recarga', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(taxApi.getTaxConfigs).mockResolvedValue([]);
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue([]);
		vi.mocked(catApi.createCategory).mockResolvedValueOnce(makeCategory('cat-new') as never);

		const { settingsStore } = await import('$lib/stores/settings');
		await settingsStore.load();
		vi.mocked(catApi.getCategories).mockClear();

		await settingsStore.createCategory({ name: 'Nueva' });

		expect(catApi.createCategory).toHaveBeenCalledTimes(1);
		expect(catApi.getCategories).toHaveBeenCalled();
	});

	it('deleteCategory aplica optimistic update', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(taxApi.getTaxConfigs).mockResolvedValue([]);
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue([]);
		vi.mocked(catApi.deleteCategory).mockResolvedValueOnce(undefined);

		const { settingsStore, settingsCategories } = await import('$lib/stores/settings');
		await settingsStore.load();

		expect(get(settingsCategories)).toHaveLength(3);
		await settingsStore.deleteCategory('cat-custom-1');
		expect(get(settingsCategories)).toHaveLength(2);
	});

	it('createTaxConfig llama a la API y fuerza recarga', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue([]);
		vi.mocked(taxApi.getTaxConfigs).mockResolvedValue(mockTaxConfigs as never);
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue([]);
		vi.mocked(taxApi.createTaxConfig).mockResolvedValueOnce({
			id: 'cfg-2',
			tax_year: 2026,
			gross_annual_salary: 40000,
			created_at: '',
			updated_at: ''
		});

		const { settingsStore } = await import('$lib/stores/settings');
		await settingsStore.load();
		vi.mocked(taxApi.getTaxConfigs).mockClear();

		await settingsStore.createTaxConfig({ tax_year: 2026, gross_annual_salary: 40000 });

		expect(taxApi.createTaxConfig).toHaveBeenCalledTimes(1);
		expect(taxApi.getTaxConfigs).toHaveBeenCalled();
	});

	it('deleteTaxConfig aplica optimistic update', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue([]);
		vi.mocked(taxApi.getTaxConfigs).mockResolvedValue(mockTaxConfigs as never);
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue([]);
		vi.mocked(taxApi.deleteTaxConfig).mockResolvedValueOnce(undefined);

		const { settingsStore, settingsTaxConfigs } = await import('$lib/stores/settings');
		await settingsStore.load();

		expect(get(settingsTaxConfigs)).toHaveLength(1);
		await settingsStore.deleteTaxConfig('cfg-1');
		expect(get(settingsTaxConfigs)).toHaveLength(0);
	});

	it('settingsCustomCategories filtra solo las no-sistema', async () => {
		const catApi = await import('$lib/api/categories');
		const taxApi = await import('$lib/api/tax');
		vi.mocked(catApi.getCategories).mockResolvedValue(mockCategories as never);
		vi.mocked(taxApi.getTaxConfigs).mockResolvedValue([]);
		vi.mocked(taxApi.getTaxBrackets).mockResolvedValue([]);

		const { settingsStore, settingsCustomCategories, settingsSystemCategories } =
			await import('$lib/stores/settings');
		await settingsStore.load();

		expect(get(settingsCustomCategories)).toHaveLength(1);
		expect(get(settingsSystemCategories)).toHaveLength(2);
	});
});
