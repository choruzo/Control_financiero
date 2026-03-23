<script lang="ts">
	import { onDestroy } from 'svelte';
	import { formatMonth, formatCurrency } from '$lib/utils/format';
	import type { CashflowMonth } from '$lib/types';

	export let data: CashflowMonth[] = [];
	export let loading: boolean = false;

	let chartEl: HTMLDivElement;
	let chart: { setOption: (o: object, replace?: boolean) => void; resize: () => void; dispose: () => void } | null = null;
	let resizeObserver: ResizeObserver;

	// Inicializar ECharts en cuanto chartEl esté en el DOM (puede que loading=true al montar)
	$: if (chartEl && !chart) {
		import('echarts').then(({ init }) => {
			chart = init(chartEl, 'dark', { renderer: 'canvas' });
			resizeObserver = new ResizeObserver(() => chart?.resize());
			resizeObserver.observe(chartEl);
			if (data.length) chart.setOption(buildOption(data), true);
		});
	}

	$: if (chart && data) {
		chart.setOption(buildOption(data), true);
	}

	onDestroy(() => {
		resizeObserver?.disconnect();
		chart?.dispose();
		chart = null;
	});

	function buildOption(months: CashflowMonth[]): object {
		const labels = months.map((m) => formatMonth(m.year, m.month));
		const incomes = months.map((m) => Number(m.total_income));
		const expenses = months.map((m) => Number(m.total_expenses));

		return {
			backgroundColor: 'transparent',
			tooltip: {
				trigger: 'axis',
				axisPointer: { type: 'shadow' },
				formatter: (params: Array<{ seriesName: string; value: number; color: string }>) => {
					return params
						.map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName}: ${formatCurrency(p.value)}`)
						.join('<br/>');
				}
			},
			legend: {
				data: ['Ingresos', 'Gastos'],
				textStyle: { color: '#94a3b8' }
			},
			grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
			xAxis: {
				type: 'category',
				data: labels,
				axisLine: { lineStyle: { color: '#475569' } },
				axisLabel: { color: '#94a3b8', fontSize: 11 }
			},
			yAxis: {
				type: 'value',
				axisLabel: {
					color: '#94a3b8',
					fontSize: 11,
					formatter: (v: number) => `${(v / 1000).toFixed(0)}k€`
				},
				splitLine: { lineStyle: { color: '#334155' } }
			},
			series: [
				{
					name: 'Ingresos',
					type: 'bar',
					data: incomes,
					itemStyle: { color: '#22c55e', borderRadius: [4, 4, 0, 0] }
				},
				{
					name: 'Gastos',
					type: 'bar',
					data: expenses,
					itemStyle: { color: '#ef4444', borderRadius: [4, 4, 0, 0] }
				}
			]
		};
	}
</script>

<div class="card p-4 bg-surface-700 space-y-2">
	<h3 class="text-sm font-medium text-surface-300">Cash flow mensual</h3>
	{#if loading}
		<div class="animate-pulse h-64 bg-surface-600 rounded"></div>
	{:else if data.length === 0}
		<div class="h-64 flex items-center justify-center">
			<p class="text-surface-500 text-sm">Sin datos de cash flow disponibles</p>
		</div>
	{:else}
		<div
			bind:this={chartEl}
			class="w-full h-64"
			aria-label="Gráfico de cash flow mensual: ingresos y gastos de los últimos 12 meses"
		></div>
	{/if}
</div>
