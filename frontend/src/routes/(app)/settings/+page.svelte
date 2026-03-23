<script lang="ts">
	import { onMount } from 'svelte';
	import { TabGroup, Tab, LightSwitch } from '@skeletonlabs/skeleton';
	import {
		settingsStore,
		settingsCategories,
		settingsCustomCategories,
		settingsSystemCategories,
		settingsTaxConfigs,
		settingsTaxBrackets,
		settingsLoading,
		settingsError
	} from '$lib/stores/settings';
	import ProfileSection from '$lib/components/settings/ProfileSection.svelte';
	import CategoryRow from '$lib/components/settings/CategoryRow.svelte';
	import CategoryForm from '$lib/components/settings/CategoryForm.svelte';
	import TaxConfigCard from '$lib/components/settings/TaxConfigCard.svelte';
	import TaxConfigForm from '$lib/components/settings/TaxConfigForm.svelte';
	import type { CategoryResponse, TaxConfigResponse, CategoryCreate, CategoryUpdate, TaxConfigCreate, TaxConfigUpdate } from '$lib/types';

	let activeTab = 0;

	// Categorías
	let showCategoryForm = false;
	let editingCategory: CategoryResponse | null = null;
	let categorySearch = '';
	let showSystemCategories = false;

	// Tax
	let showTaxForm = false;
	let editingTaxConfig: TaxConfigResponse | null = null;
	let selectedBracketYear = new Date().getFullYear();
	let selectedBracketType: 'general' | 'savings' = 'general';

	// Exportación
	let exporting = false;
	let exportError = '';

	onMount(() => {
		settingsStore.load();
	});

	// ── Categorías ──────────────────────────────────────────────────────────────

	$: filteredCategories = $settingsCategories.filter((c) => {
		const matchesSearch = !categorySearch || c.name.toLowerCase().includes(categorySearch.toLowerCase());
		const matchesToggle = showSystemCategories || !c.is_system;
		return matchesSearch && matchesToggle;
	});

	function openNewCategory() {
		editingCategory = null;
		showCategoryForm = true;
	}

	function openEditCategory(category: CategoryResponse) {
		editingCategory = category;
		showCategoryForm = true;
	}

	async function handleCategorySave(e: CustomEvent<{ data: CategoryCreate | CategoryUpdate; id?: string }>) {
		showCategoryForm = false;
		if (e.detail.id) {
			await settingsStore.updateCategory(e.detail.id, e.detail.data as CategoryUpdate);
		} else {
			await settingsStore.createCategory(e.detail.data as CategoryCreate);
		}
	}

	async function handleCategoryDelete(e: CustomEvent<{ id: string }>) {
		await settingsStore.deleteCategory(e.detail.id);
	}

	// ── Tax ─────────────────────────────────────────────────────────────────────

	$: existingTaxYears = $settingsTaxConfigs.map((c) => c.tax_year);

	$: filteredBrackets = $settingsTaxBrackets.filter(
		(b) => b.bracket_type === selectedBracketType
	);

	function openNewTaxConfig() {
		editingTaxConfig = null;
		showTaxForm = true;
	}

	function openEditTaxConfig(config: TaxConfigResponse) {
		editingTaxConfig = config;
		showTaxForm = true;
	}

	async function handleTaxSave(e: CustomEvent<{ data: TaxConfigCreate | TaxConfigUpdate; id?: string }>) {
		showTaxForm = false;
		if (e.detail.id) {
			await settingsStore.updateTaxConfig(e.detail.id, e.detail.data as TaxConfigUpdate);
		} else {
			await settingsStore.createTaxConfig(e.detail.data as TaxConfigCreate);
		}
	}

	async function handleTaxDelete(e: CustomEvent<{ id: string }>) {
		await settingsStore.deleteTaxConfig(e.detail.id);
	}

	async function loadBracketsForYear() {
		const { getTaxBrackets } = await import('$lib/api/tax');
		try {
			const brackets = await getTaxBrackets(selectedBracketYear);
			// Actualiza los tramos en el store directamente via reload
			await settingsStore.load(true);
		} catch {
			// ignorar
		}
	}

	// ── Exportación ─────────────────────────────────────────────────────────────

	async function exportTransactions() {
		exporting = true;
		exportError = '';
		try {
			const { getTransactions } = await import('$lib/api/transactions');
			const data = await getTransactions({ per_page: 10000 });

			const headers = ['Fecha', 'Descripción', 'Importe', 'Tipo', 'Notas'];
			const rows = data.items.map((t) => [
				t.date,
				`"${(t.description ?? '').replace(/"/g, '""')}"`,
				t.amount,
				t.transaction_type,
				`"${(t.notes ?? '').replace(/"/g, '""')}"`
			]);

			const csvContent = [headers.join(';'), ...rows.map((r) => r.join(';'))].join('\n');
			const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `transacciones_${new Date().toISOString().slice(0, 10)}.csv`;
			a.click();
			URL.revokeObjectURL(url);
		} catch {
			exportError = 'Error al exportar las transacciones';
		} finally {
			exporting = false;
		}
	}
</script>

<div class="space-y-6">
	<!-- Cabecera -->
	<div>
		<h2 class="h3">Configuración</h2>
		<p class="text-surface-400 text-sm mt-1">Gestiona tu perfil, categorías, fiscalidad y preferencias</p>
	</div>

	{#if $settingsError}
		<aside class="alert variant-ghost-error">
			<p>{$settingsError}</p>
			<button class="btn btn-sm" on:click={() => settingsStore.load(true)}>Reintentar</button>
		</aside>
	{/if}

	<TabGroup>
		<Tab bind:group={activeTab} name="tab-perfil" value={0}>👤 Perfil</Tab>
		<Tab bind:group={activeTab} name="tab-categorias" value={1}>
			🏷️ Categorías
			{#if $settingsLoading}
				<span class="badge variant-ghost text-xs ml-1">…</span>
			{:else}
				<span class="badge variant-ghost text-xs ml-1">{$settingsCustomCategories.length}</span>
			{/if}
		</Tab>
		<Tab bind:group={activeTab} name="tab-fiscal" value={2}>
			💼 Fiscal
			{#if !$settingsLoading && $settingsTaxConfigs.length > 0}
				<span class="badge variant-ghost text-xs ml-1">{$settingsTaxConfigs.length}</span>
			{/if}
		</Tab>
		<Tab bind:group={activeTab} name="tab-preferencias" value={3}>⚙️ Preferencias</Tab>

		<!-- Contenido de tabs -->
		<svelte:fragment slot="panel">

			<!-- ── Tab 0: Perfil ─────────────────────────────────────────────────── -->
			{#if activeTab === 0}
				<div class="pt-4">
					<ProfileSection />
				</div>
			{/if}

			<!-- ── Tab 1: Categorías ─────────────────────────────────────────────── -->
			{#if activeTab === 1}
				<div class="pt-4 space-y-4">
					<div class="flex flex-col sm:flex-row gap-3 justify-between">
						<div class="flex items-center gap-3">
							<input
								class="input max-w-xs"
								type="search"
								placeholder="Buscar categoría…"
								bind:value={categorySearch}
							/>
							<label class="flex items-center gap-2 text-sm cursor-pointer">
								<input type="checkbox" class="checkbox" bind:checked={showSystemCategories} />
								<span>Mostrar sistema</span>
							</label>
						</div>
						<button class="btn btn-sm variant-filled-primary" on:click={openNewCategory}>
							+ Nueva categoría
						</button>
					</div>

					{#if $settingsLoading}
						<div class="space-y-1">
							{#each [1, 2, 3, 4, 5] as _}
								<div class="h-10 bg-surface-700 rounded animate-pulse"></div>
							{/each}
						</div>
					{:else if filteredCategories.length === 0}
						<div class="card p-6 text-center text-surface-400">
							{categorySearch ? 'No hay categorías que coincidan con la búsqueda' : 'No tienes categorías personalizadas'}
						</div>
					{:else}
						<div class="card divide-y divide-surface-700">
							{#each filteredCategories as category (category.id)}
								<CategoryRow
									{category}
									on:edit={(e) => openEditCategory(e.detail.category)}
									on:delete={handleCategoryDelete}
								/>
							{/each}
						</div>
					{/if}

					<div class="text-sm text-surface-400">
						{$settingsCustomCategories.length} categorías personalizadas · {$settingsSystemCategories.length} de sistema
					</div>
				</div>
			{/if}

			<!-- ── Tab 2: Fiscal ─────────────────────────────────────────────────── -->
			{#if activeTab === 2}
				<div class="pt-4 space-y-4">
					<div class="flex items-center justify-between">
						<p class="text-sm text-surface-400">Configuraciones de IRPF por año fiscal</p>
						<button class="btn btn-sm variant-filled-primary" on:click={openNewTaxConfig}>
							+ Nueva configuración
						</button>
					</div>

					{#if $settingsLoading}
						<div class="space-y-3">
							{#each [1, 2] as _}
								<div class="card p-4 animate-pulse">
									<div class="h-5 bg-surface-600 rounded w-24 mb-2"></div>
									<div class="h-4 bg-surface-600 rounded w-48"></div>
								</div>
							{/each}
						</div>
					{:else if $settingsTaxConfigs.length === 0}
						<div class="card p-6 text-center space-y-2">
							<p class="text-surface-400">No hay configuraciones fiscales</p>
							<p class="text-sm text-surface-500">Añade tu sueldo bruto anual para calcular retención IRPF y SS</p>
							<button class="btn btn-sm variant-ghost-primary" on:click={openNewTaxConfig}>
								Crear primera configuración
							</button>
						</div>
					{:else}
						<div class="space-y-3">
							{#each $settingsTaxConfigs.sort((a, b) => b.tax_year - a.tax_year) as config (config.id)}
								<TaxConfigCard
									{config}
									on:edit={(e) => openEditTaxConfig(e.detail.config)}
									on:delete={handleTaxDelete}
								/>
							{/each}
						</div>
					{/if}

					<!-- Tabla de tramos IRPF -->
					<div class="space-y-3">
						<div class="flex items-center gap-3">
							<h3 class="font-semibold text-surface-200">Tramos IRPF vigentes</h3>
							<select class="select w-28" bind:value={selectedBracketType}>
								<option value="general">General</option>
								<option value="savings">Ahorro</option>
							</select>
						</div>

						{#if $settingsTaxBrackets.length === 0}
							<p class="text-surface-400 text-sm">No se pudieron cargar los tramos</p>
						{:else}
							<div class="table-container">
								<table class="table table-hover text-sm">
									<thead>
										<tr>
											<th>Desde (€)</th>
											<th>Hasta (€)</th>
											<th>Tipo (%)</th>
										</tr>
									</thead>
									<tbody>
										{#each filteredBrackets.sort((a, b) => Number(a.min_amount) - Number(b.min_amount)) as bracket}
											<tr>
												<td class="font-mono">{Number(bracket.min_amount).toLocaleString('es-ES')}</td>
												<td class="font-mono">{bracket.max_amount !== null ? Number(bracket.max_amount).toLocaleString('es-ES') : '∞'}</td>
												<td class="font-mono font-semibold">{(Number(bracket.rate) * 100).toFixed(0)}%</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- ── Tab 3: Preferencias ───────────────────────────────────────────── -->
			{#if activeTab === 3}
				<div class="pt-4 space-y-6">
					<!-- Tema -->
					<div class="card p-4 space-y-3">
						<h3 class="font-semibold text-surface-200">Apariencia</h3>
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm font-medium">Tema claro / oscuro</p>
								<p class="text-xs text-surface-400">Cambia entre tema claro y oscuro</p>
							</div>
							<LightSwitch />
						</div>
					</div>

					<!-- Exportación -->
					<div class="card p-4 space-y-3">
						<h3 class="font-semibold text-surface-200">Exportación de datos</h3>
						<p class="text-sm text-surface-400">
							Descarga tus transacciones en formato CSV compatible con Excel y otras herramientas.
						</p>

						{#if exportError}
							<aside class="alert variant-ghost-error text-sm">{exportError}</aside>
						{/if}

						<button
							class="btn variant-filled-secondary"
							on:click={exportTransactions}
							disabled={exporting}
						>
							{#if exporting}
								<span class="animate-spin mr-2">⟳</span> Exportando…
							{:else}
								⬇ Exportar transacciones (CSV)
							{/if}
						</button>

						<p class="text-xs text-surface-500">
							El archivo incluye: fecha, descripción, importe, tipo y notas. Separador: punto y coma (;). Codificación: UTF-8 con BOM.
						</p>
					</div>

					<!-- Info de la app -->
					<div class="card p-4 space-y-2">
						<h3 class="font-semibold text-surface-200">Acerca de FinControl</h3>
						<p class="text-sm text-surface-400">Aplicación personal de análisis financiero con IA.</p>
						<p class="text-xs text-surface-500">Stack: SvelteKit · FastAPI · PostgreSQL · Redis · PyTorch</p>
					</div>
				</div>
			{/if}

		</svelte:fragment>
	</TabGroup>
</div>

<!-- Modales -->
<CategoryForm
	show={showCategoryForm}
	{editingCategory}
	parentCategories={$settingsSystemCategories}
	on:save={handleCategorySave}
	on:close={() => (showCategoryForm = false)}
/>

<TaxConfigForm
	show={showTaxForm}
	{editingTaxConfig}
	{existingTaxYears}
	on:save={handleTaxSave}
	on:close={() => (showTaxForm = false)}
/>
