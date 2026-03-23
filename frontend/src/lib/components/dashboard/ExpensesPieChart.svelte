<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { formatCurrency, formatPercent } from '$lib/utils/format';
	import type { CategoryExpense } from '$lib/types';

	export let data: CategoryExpense[] = [];
	export let loading: boolean = false;

	let chartEl: HTMLDivElement;
	let chart: { setOption: (o: object, replace?: boolean) => void; resize: () => void; dispose: () => void } | null = null;
	let resizeObserver: ResizeObserver;

	$: if (chart && data) {
		chart.setOption(buildOption(data), true);
	}

	onMount(async () => {
		const { init } = await import('echarts');
		chart = init(chartEl, 'dark', { renderer: 'canvas' });

		resizeObserver = new ResizeObserver(() => chart?.resize());
		resizeObserver.observe(chartEl);

		if (data.length) chart.setOption(buildOption(data), true);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		chart?.dispose();
		chart = null;
	});

	const PALETTE = [
		'#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#3b82f6',
		'#ec4899', '#14b8a6', '#f97316', '#8b5cf6', '#06b6d4'
	];

	function buildOption(categories: CategoryExpense[]): object {
		const pieData = categories.map((c, i) => ({
			name: c.category_name,
			value: Number(c.total_amount),
			itemStyle: { color: PALETTE[i % PALETTE.length] }
		}));

		return {
			backgroundColor: 'transparent',
			tooltip: {
				trigger: 'item',
				formatter: (p: { name: string; value: number; percent: number }) =>
					`${p.name}<br/>${formatCurrency(p.value)} (${formatPercent(p.percent, 1)})`
			},
			legend: {
				orient: 'vertical',
				right: '2%',
				top: 'center',
				textStyle: { color: '#94a3b8', fontSize: 11 },
				itemWidth: 10,
				itemHeight: 10
			},
			series: [
				{
					type: 'pie',
					radius: ['40%', '68%'],
					center: ['38%', '50%'],
					data: pieData,
					label: { show: false },
					emphasis: {
						itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' }
					}
				}
			]
		};
	}
</script>

<div class="card p-4 bg-surface-700 space-y-2">
	<h3 class="text-sm font-medium text-surface-300">Gastos por categoría</h3>
	{#if loading}
		<div class="animate-pulse h-64 bg-surface-600 rounded"></div>
	{:else if data.length === 0}
		<div class="h-64 flex items-center justify-center">
			<p class="text-surface-500 text-sm">Sin gastos registrados este mes</p>
		</div>
	{:else}
		<div
			bind:this={chartEl}
			class="w-full h-64"
			aria-label="Gráfico de gastos por categoría del mes actual"
		></div>
	{/if}
</div>
