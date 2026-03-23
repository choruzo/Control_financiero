<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { formatMonth, formatCurrency } from '$lib/utils/format';
	import type { ForecastMonth } from '$lib/types';

	export let data: ForecastMonth[] = [];
	export let loading: boolean = false;

	let chartEl: HTMLDivElement;
	let chart: { setOption: (o: object, replace?: boolean) => void; resize: () => void; dispose: () => void } | null = null;
	let resizeObserver: ResizeObserver;

	$: if (chart && data.length) {
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

	function buildOption(months: ForecastMonth[]): object {
		const labels = months.map((m) => formatMonth(m.year, m.month));

		// Bandas de confianza como areas apiladas: [p10, p90-p10]
		const incomeP10 = months.map((m) => Number(m.income_p10));
		const incomeP50 = months.map((m) => Number(m.income_p50));
		const incomeP90 = months.map((m) => Number(m.income_p90));
		const expensesP10 = months.map((m) => Number(m.expenses_p10));
		const expensesP50 = months.map((m) => Number(m.expenses_p50));
		const expensesP90 = months.map((m) => Number(m.expenses_p90));

		// Para banda: serie base (p10) invisible + serie encima (p90-p10) semitransparente
		const incomeBandBase = incomeP10;
		const incomeBandTop = months.map((m) => Number(m.income_p90) - Number(m.income_p10));
		const expensesBandBase = expensesP10;
		const expensesBandTop = months.map((m) => Number(m.expenses_p90) - Number(m.expenses_p10));

		return {
			backgroundColor: 'transparent',
			tooltip: {
				trigger: 'axis',
				axisPointer: { type: 'cross' },
				formatter: (params: Array<{ seriesName: string; value: number; color: string }>) => {
					const visible = params.filter(
						(p) => !p.seriesName.includes('_band')
					);
					return visible
						.map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName}: ${formatCurrency(p.value)}`)
						.join('<br/>');
				}
			},
			legend: {
				data: ['Ingresos P50', 'Gastos P50'],
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
				// Banda ingresos (base invisible)
				{
					name: 'income_band_base',
					type: 'line',
					data: incomeBandBase,
					lineStyle: { opacity: 0 },
					stack: 'income_band',
					symbol: 'none',
					legendHoverLink: false,
					tooltip: { show: false }
				},
				// Banda ingresos (relleno P10-P90)
				{
					name: 'income_band_top',
					type: 'line',
					data: incomeBandTop,
					lineStyle: { opacity: 0 },
					stack: 'income_band',
					symbol: 'none',
					areaStyle: { color: '#22c55e', opacity: 0.15 },
					legendHoverLink: false,
					tooltip: { show: false }
				},
				// Línea ingresos P50
				{
					name: 'Ingresos P50',
					type: 'line',
					data: incomeP50,
					smooth: true,
					lineStyle: { color: '#22c55e', width: 2 },
					itemStyle: { color: '#22c55e' },
					symbol: 'circle',
					symbolSize: 5
				},
				// Banda gastos (base invisible)
				{
					name: 'expenses_band_base',
					type: 'line',
					data: expensesBandBase,
					lineStyle: { opacity: 0 },
					stack: 'expenses_band',
					symbol: 'none',
					legendHoverLink: false,
					tooltip: { show: false }
				},
				// Banda gastos (relleno P10-P90)
				{
					name: 'expenses_band_top',
					type: 'line',
					data: expensesBandTop,
					lineStyle: { opacity: 0 },
					stack: 'expenses_band',
					symbol: 'none',
					areaStyle: { color: '#f43f5e', opacity: 0.15 },
					legendHoverLink: false,
					tooltip: { show: false }
				},
				// Línea gastos P50
				{
					name: 'Gastos P50',
					type: 'line',
					data: expensesP50,
					smooth: true,
					lineStyle: { color: '#f43f5e', width: 2 },
					itemStyle: { color: '#f43f5e' },
					symbol: 'circle',
					symbolSize: 5
				}
			]
		};
	}
</script>

<div class="card p-4 bg-surface-700 space-y-2">
	<h3 class="text-sm font-medium text-surface-300">Predicción de flujo de caja</h3>
	{#if loading}
		<div class="animate-pulse h-72 bg-surface-600 rounded"></div>
	{:else if data.length === 0}
		<div class="h-72 flex items-center justify-center">
			<p class="text-surface-500 text-sm">Sin datos de predicción disponibles</p>
		</div>
	{:else}
		<div
			bind:this={chartEl}
			class="w-full h-72"
			aria-label="Gráfico de predicción de flujo de caja con bandas de confianza P10/P90"
		></div>
		<p class="text-xs text-surface-500 text-center">Banda sombreada = intervalo de confianza P10–P90</p>
	{/if}
</div>
