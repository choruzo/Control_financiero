<script lang="ts">
	import { onMount } from 'svelte';
	import {
		budgetsStore,
		budgetsData,
		budgetsHistory,
		budgetsCategories,
		budgetsLoading,
		budgetsError,
		budgetsPeriod
	} from '$lib/stores/budgets';
	import BudgetCard from '$lib/components/budgets/BudgetCard.svelte';
	import BudgetForm from '$lib/components/budgets/BudgetForm.svelte';
	import BudgetHistoryChart from '$lib/components/budgets/BudgetHistoryChart.svelte';
	import { formatCurrency, formatPercent, formatMonth } from '$lib/utils/format';
	import type { BudgetResponse } from '$lib/types';

	// Estado local de UI
	let showForm = false;
	let editingBudget: BudgetResponse | null = null;

	// Período de navegación (inicializado con la fecha actual)
	const today = new Date();
	let navYear = today.getFullYear();
	let navMonth = today.getMonth() + 1;

	const MONTH_NAMES_LONG = [
		'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
		'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
	];

	onMount(() => {
		budgetsStore.load(navYear, navMonth);
	});

	function prevMonth() {
		if (navMonth === 1) { navMonth = 12; navYear -= 1; }
		else navMonth -= 1;
		budgetsStore.load(navYear, navMonth);
	}

	function nextMonth() {
		if (navMonth === 12) { navMonth = 1; navYear += 1; }
		else navMonth += 1;
		budgetsStore.load(navYear, navMonth);
	}

	function openNewForm() {
		editingBudget = null;
		showForm = true;
	}

	function openEditForm(budget: BudgetResponse) {
		editingBudget = budget;
		showForm = true;
	}

	function handleFormSaved() {
		// El store ya recarga internamente al crear; al editar actualiza optimistamente
		// Forzamos refresh para sincronizar statuses (porcentajes, etc.)
		budgetsStore.refresh(navYear, navMonth);
	}

	async function handleDelete(id: string) {
		try {
			await budgetsStore.deleteBudget(id);
		} catch (e) {
			console.error('Error al eliminar presupuesto:', e);
		}
	}

	// Lookup de nombre de categoría
	function getCategoryName(categoryId: string): string {
		return $budgetsCategories.find((c) => c.id === categoryId)?.name ?? '—';
	}

	// IDs de categorías ya usadas en el período actual
	$: usedCategoryIds = $budgetsData.map((s) => s.budget.category_id);

	// KPIs agregados
	$: totalLimit = $budgetsData.reduce((sum, s) => sum + s.budget.limit_amount, 0);
	$: totalSpent = $budgetsData.reduce((sum, s) => sum + s.spent_amount, 0);
	$: avgPct = $budgetsData.length
		? $budgetsData.reduce((sum, s) => sum + s.percentage_used, 0) / $budgetsData.length
		: 0;

	// Skeletons para carga
	const SKELETON_COUNT = 4;
</script>

<div class="space-y-6">
	<!-- Cabecera -->
	<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
		<div class="flex items-center gap-3">
			<h2 class="h3">Presupuestos</h2>
			<!-- Navegación de mes -->
			<div class="flex items-center gap-1 bg-surface-700 rounded-lg px-2 py-1">
				<button
					class="btn btn-sm variant-ghost-surface"
					on:click={prevMonth}
					aria-label="Mes anterior"
				>
					‹
				</button>
				<span class="text-sm font-medium text-surface-200 min-w-[110px] text-center">
					{MONTH_NAMES_LONG[navMonth - 1]} {navYear}
				</span>
				<button
					class="btn btn-sm variant-ghost-surface"
					on:click={nextMonth}
					aria-label="Mes siguiente"
				>
					›
				</button>
			</div>
		</div>
		<button
			type="button"
			class="btn btn-sm variant-filled-primary"
			on:click={openNewForm}
		>
			+ Nuevo presupuesto
		</button>
	</div>

	<!-- KPIs -->
	<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
		<div class="card p-4 bg-surface-700 space-y-1">
			<p class="text-xs text-surface-400 uppercase tracking-wide">Total presupuestado</p>
			{#if $budgetsLoading}
				<div class="animate-pulse h-6 bg-surface-600 rounded w-3/4"></div>
			{:else}
				<p class="text-xl font-semibold text-surface-100">{formatCurrency(totalLimit)}</p>
			{/if}
		</div>
		<div class="card p-4 bg-surface-700 space-y-1">
			<p class="text-xs text-surface-400 uppercase tracking-wide">Total gastado</p>
			{#if $budgetsLoading}
				<div class="animate-pulse h-6 bg-surface-600 rounded w-3/4"></div>
			{:else}
				<p class="text-xl font-semibold {totalSpent > totalLimit ? 'text-error-400' : 'text-surface-100'}">
					{formatCurrency(totalSpent)}
				</p>
			{/if}
		</div>
		<div class="card p-4 bg-surface-700 space-y-1">
			<p class="text-xs text-surface-400 uppercase tracking-wide">% Medio consumido</p>
			{#if $budgetsLoading}
				<div class="animate-pulse h-6 bg-surface-600 rounded w-3/4"></div>
			{:else}
				<p class="text-xl font-semibold {avgPct >= 100 ? 'text-error-400' : avgPct >= 80 ? 'text-warning-400' : 'text-surface-100'}">
					{formatPercent(avgPct)}
				</p>
			{/if}
		</div>
	</div>

	<!-- Error -->
	{#if $budgetsError}
		<div class="alert variant-filled-error">
			<span>{$budgetsError}</span>
			<button class="btn btn-sm variant-ghost-surface ml-auto" on:click={() => budgetsStore.refresh(navYear, navMonth)}>
				Reintentar
			</button>
		</div>
	{/if}

	<!-- Grid de tarjetas de presupuesto -->
	{#if $budgetsLoading}
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each Array(SKELETON_COUNT) as _}
				<BudgetCard
					status={{ budget: { id: '', user_id: '', category_id: '', period_year: navYear, period_month: navMonth, limit_amount: 0, alert_threshold: 80, name: null, created_at: '', updated_at: '' }, spent_amount: 0, remaining_amount: 0, percentage_used: 0, is_over_limit: false, alert_triggered: false }}
					categoryName=""
					loading={true}
				/>
			{/each}
		</div>
	{:else if $budgetsData.length === 0 && !$budgetsError}
		<!-- Estado vacío -->
		<div class="card p-12 text-center space-y-4 bg-surface-700">
			<p class="text-4xl">📋</p>
			<p class="text-lg font-medium text-surface-200">Sin presupuestos para {MONTH_NAMES_LONG[navMonth - 1]} {navYear}</p>
			<p class="text-sm text-surface-400">
				Crea presupuestos por categoría para controlar tus gastos y recibir alertas cuando los superes.
			</p>
			<button type="button" class="btn variant-filled-primary" on:click={openNewForm}>
				Crear primer presupuesto
			</button>
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each $budgetsData as status (status.budget.id)}
				<BudgetCard
					{status}
					categoryName={getCategoryName(status.budget.category_id)}
					on:edit={(e) => openEditForm(e.detail.budget)}
					on:delete={(e) => handleDelete(e.detail.id)}
				/>
			{/each}
		</div>
	{/if}

	<!-- Gráfico comparativo (visible cuando hay datos) -->
	{#if !$budgetsLoading && $budgetsData.length > 0}
		<BudgetHistoryChart
			currentStatuses={$budgetsData}
			historyStatuses={$budgetsHistory}
			currentYear={navYear}
			currentMonth={navMonth}
			categories={$budgetsCategories}
		/>
	{/if}
</div>

<!-- Modal crear/editar -->
<BudgetForm
	show={showForm}
	budget={editingBudget}
	categories={$budgetsCategories}
	{usedCategoryIds}
	year={navYear}
	month={navMonth}
	on:close={() => (showForm = false)}
	on:saved={handleFormSaved}
/>
