<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { formatCurrency, formatPercent } from '$lib/utils/format';
	import type { BudgetStatusResponse, CategoryResponse } from '$lib/types';

	export let status: BudgetStatusResponse;
	export let categoryName: string = '';
	export let loading: boolean = false;

	const dispatch = createEventDispatcher<{
		edit: { budget: BudgetStatusResponse['budget'] };
		delete: { id: string };
	}>();

	let confirmDelete = false;

	$: budget = status.budget;
	$: pct = Math.min(status.percentage_used, 100);
	$: displayName = budget.name ?? categoryName;

	// Semáforo de color
	$: barColor =
		status.is_over_limit
			? 'bg-error-500'
			: status.alert_triggered
				? 'bg-warning-500'
				: status.percentage_used >= 70
					? 'bg-warning-400'
					: 'bg-success-500';

	function handleDelete() {
		if (confirmDelete) {
			dispatch('delete', { id: budget.id });
			confirmDelete = false;
		} else {
			confirmDelete = true;
		}
	}

	function cancelDelete() {
		confirmDelete = false;
	}
</script>

<div class="card p-4 space-y-3">
	{#if loading}
		<!-- Skeleton -->
		<div class="animate-pulse space-y-3">
			<div class="h-4 bg-surface-600 rounded w-2/3"></div>
			<div class="h-3 bg-surface-600 rounded w-full"></div>
			<div class="h-2 bg-surface-700 rounded-full w-full"></div>
			<div class="h-3 bg-surface-600 rounded w-1/2"></div>
		</div>
	{:else}
		<!-- Cabecera: nombre + badges -->
		<div class="flex items-start justify-between gap-2">
			<div class="flex items-center gap-2 flex-wrap min-w-0">
				<span class="font-medium text-surface-100 truncate">{displayName}</span>
				{#if status.is_over_limit}
					<span class="badge variant-filled-error text-xs">🚨 Superado</span>
				{:else if status.alert_triggered}
					<span class="badge variant-filled-warning text-xs">⚠ Alerta</span>
				{/if}
			</div>
			<span class="text-sm font-semibold shrink-0 {status.is_over_limit ? 'text-error-400' : status.alert_triggered ? 'text-warning-400' : 'text-surface-300'}">
				{status.percentage_used.toFixed(1)}%
			</span>
		</div>

		<!-- Barra de progreso -->
		<div class="w-full bg-surface-700 rounded-full h-2.5" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
			<div
				class="h-2.5 rounded-full transition-all duration-300 {barColor}"
				style="width: {pct}%"
			></div>
		</div>

		<!-- Importes -->
		<div class="flex justify-between text-sm text-surface-300">
			<span>Gastado: <span class="text-surface-100 font-medium">{formatCurrency(status.spent_amount)}</span></span>
			<span>Límite: <span class="text-surface-100 font-medium">{formatCurrency(budget.limit_amount)}</span></span>
		</div>

		{#if status.remaining_amount < 0}
			<p class="text-xs text-error-400">
				Exceso: {formatCurrency(Math.abs(status.remaining_amount))}
			</p>
		{:else}
			<p class="text-xs text-surface-400">
				Disponible: {formatCurrency(status.remaining_amount)}
			</p>
		{/if}

		<!-- Acciones -->
		{#if confirmDelete}
			<div class="flex items-center gap-2 text-sm">
				<span class="text-warning-400 text-xs">¿Eliminar presupuesto?</span>
				<button class="btn btn-sm variant-filled-error" on:click={handleDelete}>Sí</button>
				<button class="btn btn-sm variant-ghost-surface" on:click={cancelDelete}>No</button>
			</div>
		{:else}
			<div class="flex gap-2">
				<button
					class="btn btn-sm variant-soft flex-1"
					on:click={() => dispatch('edit', { budget })}
				>
					Editar
				</button>
				<button
					class="btn btn-sm variant-ghost-error"
					on:click={handleDelete}
				>
					Eliminar
				</button>
			</div>
		{/if}
	{/if}
</div>
