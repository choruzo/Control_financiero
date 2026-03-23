<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { formatCurrency } from '$lib/utils/format';
	import type { InvestmentResponse } from '$lib/types';

	export let investments: InvestmentResponse[] = [];

	let chartEl: HTMLDivElement;
	let chart: {
		setOption: (o: object, replace?: boolean) => void;
		resize: () => void;
		dispose: () => void;
	} | null = null;
	let resizeObserver: ResizeObserver;

	const TYPE_COLORS: Record<string, string> = {
		deposit: '#3b82f6',
		fund: '#22c55e',
		stock: '#f97316',
		bond: '#a855f7'
	};

	const TYPE_LABELS: Record<string, string> = {
		deposit: 'Depósito',
		fund: 'Fondo',
		stock: 'Acciones',
		bond: 'Bono'
	};

	$: withMaturity = investments.filter((inv) => inv.maturity_date);
	$: hasData = withMaturity.length > 0;

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

	function buildOption(): object {
		// Ordenar por fecha de vencimiento
		const sorted = [...withMaturity].sort(
			(a, b) => new Date(a.maturity_date!).getTime() - new Date(b.maturity_date!).getTime()
		);

		const names = sorted.map((inv) => inv.name);
		const today = Date.now();

		// Para cada inversión: barra desde start_date hasta maturity_date
		const data = sorted.map((inv, idx) => {
			const start = new Date(inv.start_date).getTime();
			const end = new Date(inv.maturity_date!).getTime();
			const daysLeft = Math.ceil((end - today) / (1000 * 60 * 60 * 24));
			return {
				name: inv.name,
				value: [idx, start, end, inv.principal_amount, inv.investment_type, daysLeft]
			};
		});

		return {
			backgroundColor: 'transparent',
			tooltip: {
				formatter: (params: { value: [number, number, number, number, string, number] }) => {
					const [, start, end, principal, type, daysLeft] = params.value;
					const startStr = new Date(start).toLocaleDateString('es-ES');
					const endStr = new Date(end).toLocaleDateString('es-ES');
					const daysStr =
						daysLeft >= 0
							? `<br/><span style="color:#f97316">Vence en ${daysLeft} días</span>`
							: `<br/><span style="color:#ef4444">Venció hace ${Math.abs(daysLeft)} días</span>`;
					return `
						<b>${(params as unknown as { name: string }).name}</b><br/>
						Tipo: ${TYPE_LABELS[type] ?? type}<br/>
						Capital: ${formatCurrency(principal)}<br/>
						${startStr} → ${endStr}${daysStr}
					`;
				}
			},
			grid: { left: '2%', right: '3%', bottom: '5%', containLabel: true },
			xAxis: {
				type: 'time',
				axisLabel: {
					color: '#94a3b8',
					fontSize: 10,
					formatter: (val: number) =>
						new Date(val).toLocaleDateString('es-ES', { month: 'short', year: '2-digit' })
				},
				axisLine: { lineStyle: { color: '#475569' } },
				splitLine: { lineStyle: { color: '#1e293b' } }
			},
			yAxis: {
				type: 'category',
				data: names,
				axisLabel: {
					color: '#94a3b8',
					fontSize: 10,
					formatter: (val: string) => (val.length > 16 ? val.slice(0, 14) + '…' : val)
				},
				axisLine: { lineStyle: { color: '#475569' } }
			},
			series: [
				{
					type: 'custom',
					renderItem: (
						params: { coordSys: { x: number; y: number; width: number; height: number } },
						api: {
							value: (idx: number) => number;
							coord: (pos: [number, number]) => [number, number];
							size: (val: [number, number]) => [number, number];
							style: (opt: object) => object;
						}
					) => {
						const categoryIndex = api.value(0);
						const start = api.coord([api.value(1), categoryIndex]);
						const end = api.coord([api.value(2), categoryIndex]);
						const height = api.size([0, 1])[1] * 0.5;
						const rectShape = {
							x: start[0],
							y: start[1] - height / 2,
							width: end[0] - start[0],
							height
						};
						const clippedShape = {
							x: Math.max(rectShape.x, params.coordSys.x),
							y: rectShape.y,
							width:
								Math.min(rectShape.x + rectShape.width, params.coordSys.x + params.coordSys.width) -
								Math.max(rectShape.x, params.coordSys.x),
							height: rectShape.height
						};
						if (clippedShape.width <= 0) return null;
						return {
							type: 'rect',
							shape: clippedShape,
							style: api.style({
								fill: TYPE_COLORS[api.value(4) as unknown as string] ?? '#3b82f6',
								opacity: 0.8
							})
						};
					},
					encode: { x: [1, 2], y: 0 },
					data
				},
				// Línea "hoy"
				{
					type: 'line',
					markLine: {
						silent: true,
						symbol: 'none',
						data: [{ xAxis: today }],
						lineStyle: { color: '#f43f5e', type: 'dashed', width: 1.5 },
						label: {
							formatter: 'Hoy',
							position: 'insideEndTop',
							color: '#f43f5e',
							fontSize: 10
						}
					},
					data: []
				}
			]
		};
	}
</script>

<div class="card p-4 bg-surface-700 space-y-2">
	<h3 class="text-sm font-medium text-surface-300">Timeline de Vencimientos</h3>
	{#if !hasData}
		<div class="h-48 flex items-center justify-center">
			<p class="text-surface-500 text-sm">Sin vencimientos registrados</p>
		</div>
	{:else}
		<div
			bind:this={chartEl}
			style="height: {Math.max(180, withMaturity.length * 48)}px"
			class="w-full"
			aria-label="Gráfico de timeline de vencimientos de inversiones"
		></div>
	{/if}
</div>
