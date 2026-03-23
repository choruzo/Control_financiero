<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { MortgageSimulationResult } from '$lib/types';
	import { formatCurrency, formatPercent } from '$lib/utils/format';

	export let result: MortgageSimulationResult | null = null;
	export let loading = false;

	let activeView: 'chart' | 'table' = 'chart';
	let chartEl: HTMLDivElement;
	let chart: { setOption: (o: object, r?: boolean) => void; resize: () => void; dispose: () => void } | null = null;
	let resizeObserver: ResizeObserver;

	// Muestra solo filas anuales (mes 12, 24, 36...) para no saturar
	$: annualRows = result?.schedule.filter((r) => r.month % 12 === 0) ?? [];

	$: if (chart && result) {
		chart.setOption(buildOption(), true);
	}

	onMount(async () => {
		const { init } = await import('echarts');
		chart = init(chartEl, 'dark', { renderer: 'canvas' });
		resizeObserver = new ResizeObserver(() => chart?.resize());
		resizeObserver.observe(chartEl);
		if (result) chart.setOption(buildOption(), true);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		chart?.dispose();
		chart = null;
	});

	function buildOption(): object {
		if (!result) return {};

		const labels = annualRows.map((r) => `Año ${r.month / 12}`);
		const principals = annualRows.map((r) => Number(r.principal.toFixed(2)));
		const interests = annualRows.map((r) => Number(r.interest.toFixed(2)));
		const balances = annualRows.map((r) => Number(r.balance.toFixed(2)));

		return {
			backgroundColor: 'transparent',
			tooltip: {
				trigger: 'axis',
				formatter: (params: { seriesName: string; value: number }[]) => {
					return params.map((p) => `${p.seriesName}: ${formatCurrency(p.value)}`).join('<br/>');
				}
			},
			legend: { data: ['Capital', 'Intereses', 'Saldo pendiente'], textStyle: { color: '#cbd5e1' } },
			grid: { left: '3%', right: '6%', bottom: '3%', containLabel: true },
			xAxis: { type: 'category', data: labels, axisLabel: { color: '#94a3b8' } },
			yAxis: [
				{ type: 'value', name: 'Cuota (€)', axisLabel: { color: '#94a3b8', formatter: (v: number) => `${(v / 1000).toFixed(0)}k` } },
				{ type: 'value', name: 'Saldo (€)', axisLabel: { color: '#94a3b8', formatter: (v: number) => `${(v / 1000).toFixed(0)}k` } }
			],
			series: [
				{
					name: 'Capital',
					type: 'bar',
					stack: 'cuota',
					data: principals,
					itemStyle: { color: '#3b82f6' }
				},
				{
					name: 'Intereses',
					type: 'bar',
					stack: 'cuota',
					data: interests,
					itemStyle: { color: '#f97316' }
				},
				{
					name: 'Saldo pendiente',
					type: 'line',
					yAxisIndex: 1,
					data: balances,
					smooth: true,
					lineStyle: { color: '#a78bfa', width: 2 },
					symbol: 'none'
				}
			]
		};
	}
</script>

<div class="card p-4 bg-surface-700 space-y-3">
	<div class="flex items-center justify-between">
		<h3 class="text-base font-semibold text-surface-100">Tabla de amortización</h3>
		{#if result}
			<div class="flex gap-1">
				<button
					type="button"
					class="btn btn-sm {activeView === 'chart' ? 'variant-filled-primary' : 'variant-ghost-surface'}"
					on:click={() => (activeView = 'chart')}
				>
					Gráfico
				</button>
				<button
					type="button"
					class="btn btn-sm {activeView === 'table' ? 'variant-filled-primary' : 'variant-ghost-surface'}"
					on:click={() => (activeView = 'table')}
				>
					Tabla
				</button>
			</div>
		{/if}
	</div>

	{#if loading}
		<div class="h-64 flex items-center justify-center">
			<div class="animate-pulse text-surface-400">Calculando...</div>
		</div>
	{:else if !result}
		<div class="h-64 flex flex-col items-center justify-center gap-3 text-center">
			<p class="text-4xl">📊</p>
			<p class="text-surface-400 text-sm">Completa el formulario y pulsa "Calcular" para ver la tabla de amortización</p>
		</div>
	{:else if activeView === 'chart'}
		<div bind:this={chartEl} style="height: 320px" class="w-full"></div>
	{:else}
		<div class="overflow-auto max-h-96">
			<table class="table table-compact w-full text-sm">
				<thead>
					<tr>
						<th class="text-surface-400">Mes</th>
						<th class="text-surface-400">Cuota</th>
						<th class="text-surface-400">Capital</th>
						<th class="text-surface-400">Interés</th>
						<th class="text-surface-400">Saldo</th>
						<th class="text-surface-400">Tasa</th>
					</tr>
				</thead>
				<tbody>
					{#each result.schedule as row}
						<tr class="{row.month % 12 === 0 ? 'bg-surface-600/40' : ''}">
							<td class="text-surface-300">{row.month}</td>
							<td class="text-surface-100 font-medium">{formatCurrency(row.payment)}</td>
							<td class="text-blue-400">{formatCurrency(row.principal)}</td>
							<td class="text-orange-400">{formatCurrency(row.interest)}</td>
							<td class="text-surface-200">{formatCurrency(row.balance)}</td>
							<td class="text-surface-400">{formatPercent(row.applied_rate)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

	{#if result?.closing_costs}
		{@const c = result.closing_costs}
		<details class="text-sm">
			<summary class="cursor-pointer text-surface-400 hover:text-surface-200">
				Desglose gastos de cierre — total {formatCurrency(c.total)}
			</summary>
			<div class="grid grid-cols-2 gap-x-6 gap-y-1 mt-2 pl-2 text-surface-300">
				<span>Notaría</span><span class="text-right">{formatCurrency(c.notary)}</span>
				<span>Registro</span><span class="text-right">{formatCurrency(c.registry)}</span>
				<span>Impuesto (ITP/AJD)</span><span class="text-right">{formatCurrency(c.tax)}</span>
				<span>Gestoría</span><span class="text-right">{formatCurrency(c.gestor)}</span>
				<span>Tasación</span><span class="text-right">{formatCurrency(c.appraisal)}</span>
			</div>
		</details>
	{/if}
</div>
