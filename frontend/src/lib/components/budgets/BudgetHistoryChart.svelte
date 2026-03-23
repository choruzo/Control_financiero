<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { formatCurrency, formatMonth } from '$lib/utils/format';
	import type { BudgetStatusResponse, CategoryResponse } from '$lib/types';

	/** Statuses del mes actual */
	export let currentStatuses: BudgetStatusResponse[] = [];
	/** [mes-2, mes-1] — puede tener arrays vacíos si no hay datos */
	export let historyStatuses: BudgetStatusResponse[][] = [];
	export let currentYear: number;
	export let currentMonth: number;
	export let categories: CategoryResponse[] = [];
	export let loading = false;

	let chartEl: HTMLDivElement;
	let chart: {
		setOption: (o: object, replace?: boolean) => void;
		resize: () => void;
		dispose: () => void;
	} | null = null;
	let resizeObserver: ResizeObserver;

	$: hasData = currentStatuses.length > 0;

	$: if (chart && hasData) {
		chart.setOption(buildOption(), true);
	}

	onMount(async () => {
		const { init } = await import('echarts');
		chart = init(chartEl, 'dark', { renderer: 'canvas' });
		resizeObserver = new ResizeObserver(() => chart?.resize());
		resizeObserver.observe(chartEl);
		if (hasData) chart.setOption(buildOption(), true);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		chart?.dispose();
		chart = null;
	});

	function getCategoryName(categoryId: string): string {
		return categories.find((c) => c.id === categoryId)?.name ?? categoryId.slice(0, 8) + '…';
	}

	function findSpent(statuses: BudgetStatusResponse[], categoryId: string): number {
		return statuses.find((s) => s.budget.category_id === categoryId)?.spent_amount ?? 0;
	}

	function buildOption(): object {
		// Eje X: categorías del mes actual
		const catLabels = currentStatuses.map((s) =>
			s.budget.name ?? getCategoryName(s.budget.category_id)
		);
		const catIds = currentStatuses.map((s) => s.budget.category_id);

		// 3 series: mes-2, mes-1, mes actual
		const prev2 = prevMonthInfo(2);
		const prev1 = prevMonthInfo(1);

		const COLORS = ['#475569', '#64748b', '#3b82f6'];

		const series = [
			{
				name: formatMonth(prev2.year, prev2.month),
				type: 'bar',
				data: catIds.map((id) => findSpent(historyStatuses[0] ?? [], id)),
				itemStyle: { color: COLORS[0], borderRadius: [3, 3, 0, 0] }
			},
			{
				name: formatMonth(prev1.year, prev1.month),
				type: 'bar',
				data: catIds.map((id) => findSpent(historyStatuses[1] ?? [], id)),
				itemStyle: { color: COLORS[1], borderRadius: [3, 3, 0, 0] }
			},
			{
				name: formatMonth(currentYear, currentMonth),
				type: 'bar',
				data: currentStatuses.map((s) => s.spent_amount),
				itemStyle: { color: COLORS[2], borderRadius: [3, 3, 0, 0] }
			}
		];

		return {
			backgroundColor: 'transparent',
			tooltip: {
				trigger: 'axis',
				axisPointer: { type: 'shadow' },
				formatter: (params: Array<{ seriesName: string; value: number; color: string }>) =>
					params
						.map(
							(p) =>
								`<span style="color:${p.color}">●</span> ${p.seriesName}: ${formatCurrency(p.value)}`
						)
						.join('<br/>')
			},
			legend: {
				textStyle: { color: '#94a3b8' },
				bottom: 0
			},
			grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
			xAxis: {
				type: 'category',
				data: catLabels,
				axisLabel: { color: '#94a3b8', fontSize: 10, rotate: catLabels.length > 4 ? 30 : 0 },
				axisLine: { lineStyle: { color: '#475569' } }
			},
			yAxis: {
				type: 'value',
				axisLabel: {
					color: '#94a3b8',
					fontSize: 11,
					formatter: (v: number) => `${(v / 1000).toFixed(1)}k€`
				},
				splitLine: { lineStyle: { color: '#334155' } }
			},
			series
		};
	}

	function prevMonthInfo(n: number): { year: number; month: number } {
		let m = currentMonth - n;
		let y = currentYear;
		while (m <= 0) {
			m += 12;
			y -= 1;
		}
		return { year: y, month: m };
	}
</script>

<div class="card p-4 bg-surface-700 space-y-2">
	<h3 class="text-sm font-medium text-surface-300">Comparativa mensual por categoría</h3>
	{#if loading}
		<div class="animate-pulse h-72 bg-surface-600 rounded"></div>
	{:else if !hasData}
		<div class="h-72 flex items-center justify-center">
			<p class="text-surface-500 text-sm">Sin datos de presupuesto para mostrar</p>
		</div>
	{:else}
		<div
			bind:this={chartEl}
			class="w-full h-72"
			aria-label="Gráfico comparativo de gastos por categoría en los últimos 3 meses"
		></div>
	{/if}
</div>
