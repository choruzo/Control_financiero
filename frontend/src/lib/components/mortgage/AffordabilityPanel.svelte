<script lang="ts">
	import { mortgageStore, mortgageAffordability, mortgageCalculating, mortgageError } from '$lib/stores/mortgage';
	import { formatCurrency, formatPercent } from '$lib/utils/format';

	let loadError = '';

	async function handleLoad() {
		loadError = '';
		try {
			await mortgageStore.loadAffordability();
		} catch (err) {
			loadError = err instanceof Error ? err.message : 'Error al cargar los datos';
		}
	}
</script>

<div class="space-y-5">
	{#if !$mortgageAffordability}
		<div class="card p-8 bg-surface-700 flex flex-col items-center gap-4 text-center">
			<p class="text-4xl">🏦</p>
			<div class="space-y-1">
				<p class="text-lg font-medium text-surface-200">¿Cuánta hipoteca puedes permitirte?</p>
				<p class="text-sm text-surface-400">
					Calculamos tu capacidad hipotecaria usando tus ingresos reales de los últimos 3 meses.
					Necesitas tener al menos 3 transacciones de tipo ingreso registradas.
				</p>
			</div>
			{#if loadError || $mortgageError}
				<div class="alert variant-filled-error text-sm p-2 w-full">{loadError || $mortgageError}</div>
			{/if}
			<button
				type="button"
				class="btn variant-filled-primary"
				on:click={handleLoad}
				disabled={$mortgageCalculating}
			>
				{$mortgageCalculating ? 'Calculando...' : 'Calcular capacidad'}
			</button>
		</div>
	{:else}
		{@const a = $mortgageAffordability}
		<!-- KPIs principales -->
		<div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
			<div class="card p-4 bg-surface-700 space-y-1">
				<p class="text-xs text-surface-400 uppercase tracking-wide">Ingreso neto mensual</p>
				<p class="text-xl font-bold text-surface-100">{formatCurrency(a.monthly_net_income)}</p>
				<p class="text-xs text-surface-500">Promedio últimos 3 meses</p>
			</div>
			<div class="card p-4 bg-surface-700 space-y-1">
				<p class="text-xs text-surface-400 uppercase tracking-wide">Cuota máxima recomendada</p>
				<p class="text-xl font-bold text-primary-400">{formatCurrency(a.max_monthly_payment)}</p>
				<p class="text-xs text-surface-500">35% del ingreso neto</p>
			</div>
			<div class="card p-4 bg-surface-700 space-y-1">
				<p class="text-xs text-surface-400 uppercase tracking-wide">Préstamo recomendado</p>
				<p class="text-xl font-bold text-success-400">{formatCurrency(a.recommended_max_loan)}</p>
				<p class="text-xs text-surface-500">Fijo 25 años</p>
			</div>
		</div>

		<!-- Tabla de opciones -->
		<div class="card p-4 bg-surface-700 space-y-3">
			<h3 class="text-sm font-semibold text-surface-200">Opciones de financiación</h3>
			<div class="overflow-auto">
				<table class="table w-full text-sm">
					<thead>
						<tr>
							<th class="text-surface-400 text-left">Producto</th>
							<th class="text-surface-400 text-right">Tasa</th>
							<th class="text-surface-400 text-right">Plazo</th>
							<th class="text-surface-400 text-right">Cuota mensual</th>
							<th class="text-surface-400 text-right">Préstamo máx.</th>
						</tr>
					</thead>
					<tbody>
						{#each a.options as opt}
							<tr>
								<td class="text-surface-100">{opt.description}</td>
								<td class="text-right text-surface-300">{formatPercent(opt.interest_rate)}</td>
								<td class="text-right text-surface-300">{opt.term_years} años</td>
								<td class="text-right text-primary-400 font-medium">{formatCurrency(opt.monthly_payment)}</td>
								<td class="text-right text-success-400 font-semibold">{formatCurrency(opt.max_loan)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p class="text-xs text-surface-500">
				* Cálculo orientativo basado en la regla del 35% de endeudamiento. Consulta con tu entidad bancaria.
			</p>
		</div>

		<div class="flex justify-end">
			<button
				type="button"
				class="btn btn-sm variant-ghost-surface"
				on:click={handleLoad}
				disabled={$mortgageCalculating}
			>
				{$mortgageCalculating ? 'Actualizando...' : 'Actualizar datos'}
			</button>
		</div>
	{/if}
</div>
