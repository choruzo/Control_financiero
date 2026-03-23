<script lang="ts">
	import { formatCurrency, formatPercent } from '$lib/utils/format';

	export let label: string;
	export let value: number | null = null;
	export let icon: string = '';
	export let trend: number | null = null;
	export let formatAs: 'currency' | 'percent' | 'number' = 'currency';
	export let loading: boolean = false;

	function formatValue(v: number | null): string {
		if (v === null || v === undefined) return '—';
		if (formatAs === 'currency') return formatCurrency(v);
		if (formatAs === 'percent') return formatPercent(v);
		return v.toLocaleString('es-ES');
	}

	$: trendPositive = trend !== null && trend > 0;
	$: trendNegative = trend !== null && trend < 0;
	$: trendLabel = trend !== null ? `${trend > 0 ? '+' : ''}${trend.toFixed(1)}%` : null;
</script>

<div class="card p-4 bg-surface-700 space-y-2">
	<div class="flex items-center justify-between">
		<p class="text-surface-400 text-sm">{label}</p>
		{#if icon}
			<span class="text-xl" aria-hidden="true">{icon}</span>
		{/if}
	</div>

	{#if loading}
		<div class="animate-pulse space-y-2">
			<div class="h-8 bg-surface-500 rounded w-3/4"></div>
			<div class="h-3 bg-surface-600 rounded w-1/2"></div>
		</div>
	{:else}
		<p class="text-2xl font-bold text-primary-400">{formatValue(value)}</p>
		{#if trendLabel}
			<p
				class="text-xs font-medium"
				class:text-success-400={trendPositive}
				class:text-error-400={trendNegative}
				class:text-surface-400={!trendPositive && !trendNegative}
			>
				{trendPositive ? '▲' : trendNegative ? '▼' : '—'}
				{trendLabel} vs mes anterior
			</p>
		{/if}
	{/if}
</div>
