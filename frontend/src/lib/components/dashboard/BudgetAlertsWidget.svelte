<script lang="ts">
	import { formatPercent, formatCurrency } from '$lib/utils/format';
	import type { BudgetAlertResponse } from '$lib/types';
	import { createEventDispatcher } from 'svelte';

	export let alerts: BudgetAlertResponse[] = [];
	export let loading: boolean = false;

	const dispatch = createEventDispatcher<{ markRead: string }>();

	$: sorted = [...alerts].sort(
		(a, b) => new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime()
	);
	$: visible = sorted.slice(0, 5);

	function badgeClass(percentage: number): string {
		if (percentage >= 100) return 'badge variant-filled-error';
		if (percentage >= 80) return 'badge variant-filled-warning';
		return 'badge variant-filled-surface';
	}

	function handleMarkRead(id: string) {
		dispatch('markRead', id);
	}
</script>

<div class="card p-4 bg-surface-700 space-y-3">
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-medium text-surface-300">Alertas de presupuesto</h3>
		{#if alerts.length > 0}
			<span class="badge variant-filled-error text-xs">{alerts.length}</span>
		{/if}
	</div>

	{#if loading}
		<div class="animate-pulse space-y-2">
			{#each [1, 2, 3] as _}
				<div class="h-12 bg-surface-600 rounded"></div>
			{/each}
		</div>
	{:else if visible.length === 0}
		<div class="py-6 text-center">
			<p class="text-success-400 text-2xl mb-1">✓</p>
			<p class="text-surface-400 text-sm">Todo en orden. Sin alertas activas.</p>
		</div>
	{:else}
		<ul class="space-y-2">
			{#each visible as alert (alert.id)}
				<li class="flex items-center justify-between gap-2 p-2 rounded bg-surface-600">
					<div class="flex items-center gap-2 min-w-0">
						<span class={badgeClass(alert.percentage)}>
							{formatPercent(alert.percentage, 0)}
						</span>
						<span class="text-xs text-surface-300 truncate">
							{formatCurrency(alert.spent_amount)} gastado
						</span>
					</div>
					<button
						class="btn btn-sm variant-ghost-surface text-xs shrink-0"
						on:click={() => handleMarkRead(alert.id)}
					>
						Leída
					</button>
				</li>
			{/each}
		</ul>
		<div class="text-right">
			<a href="/budgets" class="text-xs text-primary-400 hover:underline">
				Ver presupuestos →
			</a>
		</div>
	{/if}
</div>
