<script lang="ts">
	import { onMount } from 'svelte';
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';
	import {
		mortgageStore,
		mortgageSimulations,
		mortgageCurrentResult,
		mortgageLoading,
		mortgageError
	} from '$lib/stores/mortgage';
	import MortgageSimulatorForm from '$lib/components/mortgage/MortgageSimulatorForm.svelte';
	import AmortizationChart from '$lib/components/mortgage/AmortizationChart.svelte';
	import ComparisonPanel from '$lib/components/mortgage/ComparisonPanel.svelte';
	import AffordabilityPanel from '$lib/components/mortgage/AffordabilityPanel.svelte';
	import { formatCurrency, formatPercent } from '$lib/utils/format';

	let tabSet = 0;

	// Parámetros del simulador para pasar al comparador
	let simPropertyPrice = 300000;
	let simDownPayment = 60000;
	let simTermYears = 30;

	onMount(() => {
		mortgageStore.load();
	});

	function handleSimSaved() {
		mortgageStore.load(true);
		// Ir a tab de guardadas
		tabSet = 3;
	}

	async function handleLoadSimulation(sim: { id: string; property_price: number; down_payment: number; term_years: number; rate_type: string; interest_rate: number | null; euribor_rate: number | null; spread: number | null; fixed_years: number | null; review_frequency: string | null; property_type: string }) {
		// Simula con los datos guardados y navega al simulador
		await mortgageStore.simulate({
			property_price: sim.property_price,
			down_payment: sim.down_payment,
			rate_type: sim.rate_type as 'fixed' | 'variable' | 'mixed',
			term_years: sim.term_years,
			interest_rate: sim.interest_rate ?? undefined,
			euribor_rate: sim.euribor_rate ?? undefined,
			spread: sim.spread ?? undefined,
			fixed_years: sim.fixed_years ?? undefined,
			review_frequency: (sim.review_frequency as 'annual' | 'semiannual') ?? undefined,
			property_type: sim.property_type as 'new' | 'second_hand',
			include_costs: true
		});
		tabSet = 0;
	}

	async function handleDeleteSimulation(id: string) {
		await mortgageStore.deleteSimulation(id);
	}

	function formatRateType(type: string): string {
		return { fixed: 'Fijo', variable: 'Variable', mixed: 'Mixto' }[type] ?? type;
	}

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
	}

	const SKELETON_COUNT = 3;
</script>

<div class="space-y-5">
	<!-- Cabecera -->
	<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
		<div>
			<h2 class="h3">Simulador Hipotecario</h2>
			<p class="text-sm text-surface-400">Calcula, compara y guarda simulaciones de hipoteca</p>
		</div>
	</div>

	<!-- Error global -->
	{#if $mortgageError}
		<div class="alert variant-filled-error">
			<span>{$mortgageError}</span>
			<button class="btn btn-sm variant-ghost-surface ml-auto" on:click={() => mortgageStore.load(true)}>
				Reintentar
			</button>
		</div>
	{/if}

	<!-- Tabs -->
	<TabGroup>
		<Tab bind:group={tabSet} name="simulador" value={0}>Simulador</Tab>
		<Tab bind:group={tabSet} name="comparador" value={1}>Comparador</Tab>
		<Tab bind:group={tabSet} name="capacidad" value={2}>Capacidad</Tab>
		<Tab bind:group={tabSet} name="guardadas" value={3}>
			Guardadas
			{#if $mortgageSimulations.length > 0}
				<span class="badge variant-filled-primary ml-1 text-xs">{$mortgageSimulations.length}</span>
			{/if}
		</Tab>

		<svelte:fragment slot="panel">
			{#if tabSet === 0}
				<!-- ── Tab 1: Simulador ──────────────────────────────────────────────── -->
				<div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
					<MortgageSimulatorForm
						on:saved={handleSimSaved}
					/>
					<AmortizationChart result={$mortgageCurrentResult} loading={false} />
				</div>

			{:else if tabSet === 1}
				<!-- ── Tab 2: Comparador ─────────────────────────────────────────────── -->
				<div class="space-y-3">
					<div class="card p-3 bg-surface-700/50 text-sm text-surface-300 flex flex-wrap gap-4">
						<label class="flex items-center gap-2">
							<span class="text-surface-400">Precio:</span>
							<input class="input w-32 text-sm" type="number" min="1" step="1000" bind:value={simPropertyPrice} />
						</label>
						<label class="flex items-center gap-2">
							<span class="text-surface-400">Entrada:</span>
							<input class="input w-32 text-sm" type="number" min="1" step="1000" bind:value={simDownPayment} />
						</label>
						<label class="flex items-center gap-2">
							<span class="text-surface-400">Plazo:</span>
							<input class="input w-20 text-sm" type="number" min="5" max="40" bind:value={simTermYears} />
							<span class="text-surface-400">años</span>
						</label>
					</div>
					<ComparisonPanel
						propertyPrice={simPropertyPrice}
						downPayment={simDownPayment}
						termYears={simTermYears}
					/>
				</div>

			{:else if tabSet === 2}
				<!-- ── Tab 3: Capacidad ──────────────────────────────────────────────── -->
				<AffordabilityPanel />

			{:else}
				<!-- ── Tab 4: Guardadas ──────────────────────────────────────────────── -->
				{#if $mortgageLoading}
					<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
						{#each Array(SKELETON_COUNT) as _}
							<div class="card p-4 bg-surface-700 space-y-3 animate-pulse">
								<div class="h-4 bg-surface-600 rounded w-3/4"></div>
								<div class="h-3 bg-surface-600 rounded w-1/2"></div>
								<div class="h-6 bg-surface-600 rounded w-1/3"></div>
							</div>
						{/each}
					</div>
				{:else if $mortgageSimulations.length === 0}
					<div class="card p-12 text-center space-y-4 bg-surface-700">
						<p class="text-4xl">🏠</p>
						<p class="text-lg font-medium text-surface-200">No tienes simulaciones guardadas</p>
						<p class="text-sm text-surface-400">
							Ve al simulador, calcula una hipoteca y pulsa "Guardar" para almacenarla aquí.
						</p>
						<button
							type="button"
							class="btn variant-filled-primary"
							on:click={() => (tabSet = 0)}
						>
							Ir al simulador
						</button>
					</div>
				{:else}
					<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
						{#each $mortgageSimulations as sim (sim.id)}
							<div class="card p-4 bg-surface-700 space-y-3">
								<div class="flex items-start justify-between gap-2">
									<div class="space-y-0.5 min-w-0">
										<p class="text-sm font-semibold text-surface-100 truncate">{sim.name}</p>
										<p class="text-xs text-surface-500">{formatDate(sim.created_at)}</p>
									</div>
									<span class="badge variant-soft-surface text-xs shrink-0">{formatRateType(sim.rate_type)}</span>
								</div>

								<div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
									<span class="text-surface-400">Precio</span>
									<span class="text-surface-200 text-right">{formatCurrency(sim.property_price)}</span>
									<span class="text-surface-400">Préstamo</span>
									<span class="text-surface-200 text-right">{formatCurrency(sim.loan_amount)}</span>
									<span class="text-surface-400">Plazo</span>
									<span class="text-surface-200 text-right">{sim.term_years} años</span>
								</div>

								<div class="border-t border-surface-600 pt-2">
									<p class="text-xs text-surface-400">Cuota mensual</p>
									<p class="text-lg font-bold text-primary-400">{formatCurrency(sim.initial_monthly_payment)}</p>
									<p class="text-xs text-surface-500">Total: {formatCurrency(sim.total_amount_paid)}</p>
								</div>

								<div class="flex gap-2">
									<button
										type="button"
										class="btn btn-sm variant-ghost-surface flex-1"
										on:click={() => handleLoadSimulation(sim)}
									>
										Cargar
									</button>
									<button
										type="button"
										class="btn btn-sm variant-ghost-error"
										on:click={() => handleDeleteSimulation(sim.id)}
									>
										Eliminar
									</button>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			{/if}
		</svelte:fragment>
	</TabGroup>
</div>
