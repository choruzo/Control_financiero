<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { formatMonth, formatCurrency } from '$lib/utils/format';
	import type { ScenarioResponse } from '$lib/types';

	export let result: ScenarioResponse;

	let chartEl: HTMLDivElement;
	let chart: { setOption: (o: object, replace?: boolean) => void; resize: () => void; dispose: () => void } | null = null;
	let resizeObserver: ResizeObserver;

	$: if (chart && result) {
		chart.setOption(buildOption(result), true);
	}

	onMount(async () => {
		const { init } = await import('echarts');
		chart = init(chartEl, 'dark', { renderer: 'canvas' });
		resizeObserver = new ResizeObserver(() => chart?.resize());
		resizeObserver.observe(chartEl);
		chart.setOption(buildOption(result), true);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		chart?.dispose();
		chart = null;
	});

	function buildOption(r: ScenarioResponse): object {
		const months = r.monthly_results;
		const labels = months.map((m) => formatMonth(m.year, m.month));
		const baseNet = months.map((m) => Number(m.base_net));
		const scenarioP50 = months.map((m) => Number(m.scenario_net_p50));
		const scenarioP10 = months.map((m) => Number(m.scenario_net_p10));
		const scenarioP90 = months.map((m) => Number(m.scenario_net_p90));
		// Banda escenario: [p10, p90-p10]
		const bandBase = scenarioP10;
		const bandTop = months.map((m) => Number(m.scenario_net_p90) - Number(m.scenario_net_p10));

		return {
			backgroundColor: 'transparent',
			tooltip: {
				trigger: 'axis',
				axisPointer: { type: 'shadow' },
				formatter: (params: Array<{ seriesName: string; value: number; color: string }>) => {
					const visible = params.filter((p) => !['band_base', 'band_top'].includes(p.seriesName));
					return visible
						.map((p) => `<span style="color:${p.color}">●</span> ${p.seriesName}: ${formatCurrency(p.value)}`)
						.join('<br/>');
				}
			},
			legend: {
				data: ['Neto base', 'Escenario P50'],
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
					name: 'Neto base',
					type: 'bar',
					data: baseNet,
					itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] }
				},
				{
					name: 'Escenario P50',
					type: 'bar',
					data: scenarioP50,
					itemStyle: { color: '#f97316', borderRadius: [4, 4, 0, 0] }
				},
				// Banda de incertidumbre P10-P90 como líneas de área
				{
					name: 'band_base',
					type: 'line',
					data: bandBase,
					lineStyle: { opacity: 0 },
					stack: 'scenario_band',
					symbol: 'none',
					legendHoverLink: false,
					tooltip: { show: false }
				},
				{
					name: 'band_top',
					type: 'line',
					data: bandTop,
					lineStyle: { opacity: 0 },
					stack: 'scenario_band',
					symbol: 'none',
					areaStyle: { color: '#f97316', opacity: 0.12 },
					legendHoverLink: false,
					tooltip: { show: false }
				}
			]
		};
	}

	$: improvement = Number(result.summary.total_net_improvement);
	$: isPositive = improvement >= 0;
	$: pct = result.summary.net_improvement_pct;
</script>

<div class="space-y-4">
	<!-- Cabecera con resumen -->
	<div class="card p-4 bg-surface-700">
		<div class="flex items-center justify-between mb-3">
			<h3 class="font-semibold text-surface-100">
				Resultado: <span class="text-primary-400">{result.name}</span>
			</h3>
			<span
				class="badge text-sm font-medium px-3 py-1 rounded-full"
				class:variant-filled-success={isPositive}
				class:variant-filled-error={!isPositive}
			>
				{isPositive ? '▲' : '▼'} {formatCurrency(Math.abs(improvement))}
				{#if pct !== null}({pct >= 0 ? '+' : ''}{Number(pct).toFixed(1)}%){/if}
			</span>
		</div>

		<!-- Gráfico -->
		<div
			bind:this={chartEl}
			class="w-full h-64"
			aria-label="Gráfico comparativo baseline vs escenario"
		></div>
	</div>

	<!-- Tabla de métricas del resumen -->
	<div class="card p-4 bg-surface-700">
		<h4 class="text-sm font-medium text-surface-300 mb-3">Resumen del período ({result.summary.period_months} meses)</h4>
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Neto base total</p>
				<p class="font-medium">{formatCurrency(Number(result.summary.total_base_net))}</p>
			</div>
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Neto escenario P50</p>
				<p class="font-medium">{formatCurrency(Number(result.summary.total_scenario_net_p50))}</p>
			</div>
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Mejora P10</p>
				<p class="font-medium text-surface-300">{formatCurrency(Number(result.summary.total_net_improvement_p10))}</p>
			</div>
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Mejora P90</p>
				<p class="font-medium text-surface-300">{formatCurrency(Number(result.summary.total_net_improvement_p90))}</p>
			</div>
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Mejora mensual media</p>
				<p class:text-green-400={Number(result.summary.avg_monthly_improvement) >= 0} class:text-red-400={Number(result.summary.avg_monthly_improvement) < 0} class="font-medium">
					{formatCurrency(Number(result.summary.avg_monthly_improvement))}
				</p>
			</div>
			{#if result.mortgage_impact_per_month !== null}
				<div class="space-y-0.5">
					<p class="text-xs text-surface-400">Impacto hipoteca/mes</p>
					<p class="font-medium text-orange-400">{formatCurrency(Number(result.mortgage_impact_per_month))}</p>
				</div>
			{/if}
			{#if result.summary.total_tax_impact !== null}
				<div class="space-y-0.5">
					<p class="text-xs text-surface-400">Impacto fiscal total</p>
					<p class="font-medium">{formatCurrency(Number(result.summary.total_tax_impact))}</p>
				</div>
			{/if}
		</div>

		{#if !result.ml_available}
			<p class="text-xs text-yellow-400 mt-3">⚠ El servicio ML no está disponible — predicción basada en tendencias históricas</p>
		{/if}
	</div>
</div>
