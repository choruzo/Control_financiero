<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { mortgageStore, mortgageComparison, mortgageCalculating } from '$lib/stores/mortgage';
	import { formatCurrency, formatPercent } from '$lib/utils/format';
	import type { MortgageRateType, ScenarioParams } from '$lib/types';

	export let propertyPrice = 300000;
	export let downPayment = 60000;
	export let termYears = 30;

	interface ScenarioForm {
		name: string;
		rate_type: MortgageRateType;
		interest_rate: number;
		euribor_rate: number;
		spread: number;
		fixed_years: number;
	}

	const defaultScenario = (): ScenarioForm => ({
		name: '',
		rate_type: 'fixed',
		interest_rate: 3.5,
		euribor_rate: 3.5,
		spread: 0.8,
		fixed_years: 5
	});

	let scenarios: ScenarioForm[] = [
		{ ...defaultScenario(), name: 'Fijo 30 años', rate_type: 'fixed', interest_rate: 3.5 },
		{ ...defaultScenario(), name: 'Variable Euríbor+0.8', rate_type: 'variable' }
	];

	let compareError = '';

	function addScenario() {
		if (scenarios.length >= 3) return;
		scenarios = [...scenarios, { ...defaultScenario(), name: `Escenario ${scenarios.length + 1}` }];
	}

	function removeScenario(i: number) {
		scenarios = scenarios.filter((_, idx) => idx !== i);
	}

	function setRateType(scenario: ScenarioForm, value: string) {
		scenario.rate_type = value as MortgageRateType;
		scenarios = scenarios;
	}

	async function handleCompare() {
		if (scenarios.length < 2) { compareError = 'Necesitas al menos 2 escenarios'; return; }
		compareError = '';

		const scenarioParams: ScenarioParams[] = scenarios.map((s) => {
			const base: ScenarioParams = { name: s.name || `Escenario`, rate_type: s.rate_type };
			if (s.rate_type === 'fixed') return { ...base, interest_rate: s.interest_rate };
			if (s.rate_type === 'variable') return { ...base, euribor_rate: s.euribor_rate, spread: s.spread };
			return { ...base, interest_rate: s.interest_rate, euribor_rate: s.euribor_rate, spread: s.spread, fixed_years: s.fixed_years };
		});

		try {
			await mortgageStore.compare({ property_price: propertyPrice, down_payment: downPayment, term_years: termYears, scenarios: scenarioParams });
		} catch (err) {
			compareError = err instanceof Error ? err.message : 'Error al comparar';
		}
	}

	// ── Gráfico ECharts ───────────────────────────────────────────────────────
	let chartEl: HTMLDivElement;
	let chart: { setOption: (o: object, r?: boolean) => void; resize: () => void; dispose: () => void } | null = null;
	let resizeObserver: ResizeObserver;

	$: if (chart && $mortgageComparison) {
		chart.setOption(buildBarOption(), true);
	}

	onMount(async () => {
		const { init } = await import('echarts');
		chart = init(chartEl, 'dark', { renderer: 'canvas' });
		resizeObserver = new ResizeObserver(() => chart?.resize());
		resizeObserver.observe(chartEl);
		if ($mortgageComparison) chart.setOption(buildBarOption(), true);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		chart?.dispose();
		chart = null;
	});

	function buildBarOption(): object {
		const r = $mortgageComparison;
		if (!r) return {};
		const names = r.scenarios.map((s) => s.name);
		const payments = r.scenarios.map((s) => s.initial_monthly_payment);
		const interests = r.scenarios.map((s) => s.total_interest);

		return {
			backgroundColor: 'transparent',
			tooltip: { trigger: 'axis', formatter: (params: { seriesName: string; value: number }[]) => params.map((p) => `${p.seriesName}: ${formatCurrency(p.value)}`).join('<br/>') },
			legend: { data: ['Cuota mensual', 'Total intereses'], textStyle: { color: '#cbd5e1' } },
			grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
			xAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8' } },
			yAxis: { type: 'value', axisLabel: { color: '#94a3b8', formatter: (v: number) => `${(v / 1000).toFixed(0)}k` } },
			series: [
				{ name: 'Cuota mensual', type: 'bar', data: payments, itemStyle: { color: '#3b82f6' } },
				{ name: 'Total intereses', type: 'bar', data: interests, itemStyle: { color: '#f97316' } }
			]
		};
	}
</script>

<div class="space-y-5">
	<div class="card p-4 bg-surface-700 space-y-4">
		<div class="flex items-center justify-between">
			<h3 class="text-base font-semibold text-surface-100">Escenarios a comparar</h3>
			{#if scenarios.length < 3}
				<button type="button" class="btn btn-sm variant-ghost-surface" on:click={addScenario}>
					+ Añadir escenario
				</button>
			{/if}
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each scenarios as scenario, i}
				<div class="card p-3 bg-surface-600 space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium text-surface-400 uppercase">Escenario {i + 1}</span>
						{#if scenarios.length > 2}
							<button type="button" class="btn-icon btn-sm variant-ghost-error" on:click={() => removeScenario(i)}>✕</button>
						{/if}
					</div>
					<input class="input text-sm" type="text" placeholder="Nombre del escenario" bind:value={scenario.name} />
					<div class="flex gap-1">
						{#each [{ value: 'fixed', label: 'Fijo' }, { value: 'variable', label: 'Variable' }, { value: 'mixed', label: 'Mixto' }] as rt}
							<button
								type="button"
								class="btn btn-sm flex-1 {scenario.rate_type === rt.value ? 'variant-filled-primary' : 'variant-ghost-surface'}"
								on:click={() => setRateType(scenario, rt.value)}
							>
								{rt.label}
							</button>
						{/each}
					</div>

					{#if scenario.rate_type === 'fixed'}
						<label class="label text-sm">
							<span class="text-surface-300">Interés fijo (%)</span>
							<input class="input" type="number" min="0" max="15" step="0.05" bind:value={scenario.interest_rate} />
						</label>
					{:else if scenario.rate_type === 'variable'}
						<div class="grid grid-cols-2 gap-2">
							<label class="label text-sm">
								<span class="text-surface-300">Euríbor (%)</span>
								<input class="input" type="number" min="0" max="10" step="0.05" bind:value={scenario.euribor_rate} />
							</label>
							<label class="label text-sm">
								<span class="text-surface-300">Diferencial (%)</span>
								<input class="input" type="number" min="0" max="5" step="0.05" bind:value={scenario.spread} />
							</label>
						</div>
					{:else}
						<div class="grid grid-cols-2 gap-2">
							<label class="label text-sm">
								<span class="text-surface-300">Fijo inicial (%)</span>
								<input class="input" type="number" min="0" max="15" step="0.05" bind:value={scenario.interest_rate} />
							</label>
							<label class="label text-sm">
								<span class="text-surface-300">Años fijos</span>
								<input class="input" type="number" min="1" max={termYears - 1} bind:value={scenario.fixed_years} />
							</label>
							<label class="label text-sm">
								<span class="text-surface-300">Euríbor (%)</span>
								<input class="input" type="number" min="0" max="10" step="0.05" bind:value={scenario.euribor_rate} />
							</label>
							<label class="label text-sm">
								<span class="text-surface-300">Diferencial (%)</span>
								<input class="input" type="number" min="0" max="5" step="0.05" bind:value={scenario.spread} />
							</label>
						</div>
					{/if}
				</div>
			{/each}
		</div>

		{#if compareError}
			<div class="alert variant-filled-error text-sm p-2">{compareError}</div>
		{/if}

		<div class="text-sm text-surface-400">
			Inmueble: <span class="text-surface-200">{formatCurrency(propertyPrice)}</span> · Entrada: <span class="text-surface-200">{formatCurrency(downPayment)}</span> · Plazo: <span class="text-surface-200">{termYears} años</span>
		</div>

		<button
			type="button"
			class="btn variant-filled-primary w-full"
			on:click={handleCompare}
			disabled={$mortgageCalculating}
		>
			{$mortgageCalculating ? 'Comparando...' : 'Comparar escenarios'}
		</button>
	</div>

	{#if $mortgageComparison}
		{@const r = $mortgageComparison}
		<div class="card p-4 bg-surface-700 space-y-4">
			<h3 class="text-base font-semibold text-surface-100">Resultado comparativo</h3>
			<div class="overflow-auto">
				<table class="table w-full text-sm">
					<thead>
						<tr>
							<th class="text-surface-400 text-left">Escenario</th>
							<th class="text-surface-400 text-right">Cuota inicial</th>
							<th class="text-surface-400 text-right">Total pagado</th>
							<th class="text-surface-400 text-right">Total intereses</th>
							<th class="text-surface-400 text-right">Ahorro vs 1º</th>
						</tr>
					</thead>
					<tbody>
						{#each r.scenarios as s, i}
							<tr class="{i === 0 ? 'bg-primary-500/10' : ''}">
								<td class="text-surface-100 font-medium">{s.name}</td>
								<td class="text-right text-surface-100">{formatCurrency(s.initial_monthly_payment)}</td>
								<td class="text-right text-surface-200">{formatCurrency(s.total_amount_paid)}</td>
								<td class="text-right text-error-400">{formatCurrency(s.total_interest)}</td>
								<td class="text-right">
									{#if s.savings_vs_first !== null && i > 0}
										<span class="{s.savings_vs_first > 0 ? 'text-success-400' : 'text-error-400'}">
											{s.savings_vs_first > 0 ? '-' : '+'}{formatCurrency(Math.abs(s.savings_vs_first))}
										</span>
									{:else}
										<span class="text-surface-500">—</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<div bind:this={chartEl} style="height: 260px" class="w-full"></div>
		</div>
	{/if}
</div>
