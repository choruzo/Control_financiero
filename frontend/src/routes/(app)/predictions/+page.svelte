<script lang="ts">
	import { onMount } from 'svelte';
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';
	import {
		predictionsStore,
		predictionsLoading,
		predictionsCalculating,
		predictionsError,
		forecastData,
		scenarioData,
		mlStatusData
	} from '$lib/stores/predictions';
	import ForecastChart from '$lib/components/predictions/ForecastChart.svelte';
	import ScenarioForm from '$lib/components/predictions/ScenarioForm.svelte';
	import ScenarioResultsChart from '$lib/components/predictions/ScenarioResultsChart.svelte';
	import MLStatusCard from '$lib/components/predictions/MLStatusCard.svelte';
	import { formatCurrency } from '$lib/utils/format';
	import type { ScenarioRequest } from '$lib/types';

	let activeTab = 0;
	let forecastMonths = 6;
	let scenarioError = '';

	onMount(() => {
		predictionsStore.load();
	});

	async function handleForecastMonthsChange() {
		// Recarga forecast con nuevo número de meses
		const { getForecast } = await import('$lib/api/predictions');
		try {
			const result = await getForecast(forecastMonths);
			// Actualiza directamente el forecast en el store
			predictionsStore['_setForecast']?.(result);
		} catch {
			// ignorar
		}
	}

	async function handleScenarioSubmit(e: CustomEvent<ScenarioRequest>) {
		scenarioError = '';
		try {
			await predictionsStore.analyzeScenario(e.detail);
		} catch (err) {
			scenarioError = err instanceof Error ? err.message : 'Error al analizar escenario';
		}
	}

	// KPIs del próximo mes (primer punto del forecast)
	$: nextMonth = $forecastData?.predictions[0] ?? null;
	$: kpiIncome = nextMonth ? Number(nextMonth.income_p50) : null;
	$: kpiExpenses = nextMonth ? Number(nextMonth.expenses_p50) : null;
	$: kpiNet = nextMonth ? Number(nextMonth.net_p50) : null;
</script>

<div class="space-y-6">
	<!-- Cabecera -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold">Predicciones y Escenarios</h1>
			<p class="text-sm text-surface-400 mt-1">Análisis predictivo de tu flujo de caja con IA</p>
		</div>
		<button
			class="btn btn-sm variant-ghost-surface"
			on:click={() => predictionsStore.load(true)}
			disabled={$predictionsLoading}
		>
			{$predictionsLoading ? '⟳' : '↺'} Actualizar
		</button>
	</div>

	<!-- Error global -->
	{#if $predictionsError}
		<div class="alert variant-ghost-error">
			<p>{$predictionsError}</p>
			<button class="btn btn-sm variant-filled-error ml-auto" on:click={() => predictionsStore.load(true)}>
				Reintentar
			</button>
		</div>
	{/if}

	<!-- KPI cards del próximo mes -->
	<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
		{#each [
			{ label: 'Ingreso esperado (P50)', value: kpiIncome, color: 'text-green-400' },
			{ label: 'Gasto esperado (P50)', value: kpiExpenses, color: 'text-red-400' },
			{ label: 'Ahorro neto esperado', value: kpiNet, color: kpiNet !== null && kpiNet >= 0 ? 'text-green-400' : 'text-red-400' }
		] as kpi}
			<div class="card p-4 bg-surface-700 space-y-1">
				<p class="text-xs text-surface-400">{kpi.label}</p>
				{#if $predictionsLoading}
					<div class="animate-pulse h-7 bg-surface-600 rounded w-3/4"></div>
				{:else if kpi.value !== null}
					<p class="text-xl font-bold {kpi.color}">{formatCurrency(kpi.value)}</p>
					<p class="text-xs text-surface-500">Mes siguiente</p>
				{:else}
					<p class="text-surface-500 text-sm">Sin datos</p>
				{/if}
			</div>
		{/each}
	</div>

	<!-- Modelo e info -->
	{#if $forecastData && !$predictionsLoading}
		<div class="flex flex-wrap gap-3 text-xs text-surface-400">
			<span>Modelo: <span class="text-surface-200 font-medium">{$forecastData.model_used}</span></span>
			<span>Versión: <span class="text-surface-200">{$forecastData.model_version}</span></span>
			<span>Histórico: <span class="text-surface-200">{$forecastData.historical_months_used} meses</span></span>
			{#if !$forecastData.ml_available}
				<span class="text-yellow-400">⚠ Modo degradado</span>
			{/if}
		</div>
	{/if}

	<!-- Tabs -->
	<TabGroup>
		<Tab bind:group={activeTab} name="forecast" value={0}>Predicciones</Tab>
		<Tab bind:group={activeTab} name="scenarios" value={1}>Escenarios what-if</Tab>
		<Tab bind:group={activeTab} name="models" value={2}>Modelos ML</Tab>

		<svelte:fragment slot="panel">
			<!-- Tab 0: Predicciones -->
			{#if activeTab === 0}
				<div class="space-y-4 pt-2">
					<div class="flex items-center gap-4">
						<label class="text-sm text-surface-300" for="forecast-months">Meses a predecir:</label>
						<select
							id="forecast-months"
							bind:value={forecastMonths}
							on:change={handleForecastMonthsChange}
							class="select variant-form-material w-32"
						>
							<option value={3}>3 meses</option>
							<option value={6}>6 meses</option>
							<option value={12}>12 meses</option>
						</select>
					</div>

					<ForecastChart
						data={$forecastData?.predictions ?? []}
						loading={$predictionsLoading}
					/>
				</div>
			{/if}

			<!-- Tab 1: Escenarios -->
			{#if activeTab === 1}
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-2">
					<div class="space-y-4">
						<ScenarioForm
							loading={$predictionsCalculating}
							on:submit={handleScenarioSubmit}
						/>
						{#if scenarioError}
							<div class="alert variant-ghost-error text-sm">{scenarioError}</div>
						{/if}
					</div>

					<div>
						{#if $predictionsCalculating}
							<div class="card p-8 bg-surface-700 flex flex-col items-center gap-3 text-surface-400">
								<span class="text-3xl animate-spin">⟳</span>
								<p class="text-sm">Ejecutando simulación Monte Carlo...</p>
							</div>
						{:else if $scenarioData}
							<ScenarioResultsChart result={$scenarioData} />
							<button
								class="btn btn-sm variant-ghost-surface mt-3"
								on:click={() => predictionsStore.clearScenario()}
							>
								✕ Limpiar resultado
							</button>
						{:else}
							<div class="card p-8 bg-surface-700 flex flex-col items-center gap-3 text-surface-400">
								<span class="text-4xl">🔮</span>
								<p class="text-sm text-center">Configura un escenario y pulsa "Analizar" para ver el impacto en tu flujo de caja</p>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Tab 2: Modelos ML -->
			{#if activeTab === 2}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
					<MLStatusCard
						status={$mlStatusData}
						loading={$predictionsLoading}
						title="Categorizador (DistilBERT)"
					/>
					<div class="card p-4 bg-surface-700 space-y-3">
						<h3 class="font-semibold text-surface-100">Predictor de cashflow</h3>
						<p class="text-sm text-surface-400">
							Modelo LSTM bidireccional con MC Dropout para intervalos de confianza.
							{#if $forecastData}
								Último modelo usado: <span class="text-surface-200 font-medium">{$forecastData.model_used}</span>.
								Entrenado con <span class="text-surface-200">{$forecastData.historical_months_used}</span> meses de histórico.
							{:else}
								Cargando información...
							{/if}
						</p>
						{#if $forecastData && !$forecastData.ml_available}
							<p class="text-xs text-yellow-400">⚠ El servicio ML no está disponible. Las predicciones se basan en medias históricas.</p>
						{/if}
					</div>
				</div>
			{/if}
		</svelte:fragment>
	</TabGroup>
</div>
