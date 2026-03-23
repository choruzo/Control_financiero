<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { getTaxCalculation } from '$lib/api/tax';
	import { formatCurrency } from '$lib/utils/format';
	import type { TaxConfigResponse, TaxCalculationResponse } from '$lib/types';

	export let config: TaxConfigResponse;

	const dispatch = createEventDispatcher<{
		edit: { config: TaxConfigResponse };
		delete: { id: string };
	}>();

	let calculation: TaxCalculationResponse | null = null;
	let loadingCalc = false;
	let showDetail = false;
	let confirmDelete = false;

	async function toggleDetail() {
		showDetail = !showDetail;
		if (showDetail && !calculation) {
			loadingCalc = true;
			try {
				calculation = await getTaxCalculation(config.id);
			} catch {
				showDetail = false;
			} finally {
				loadingCalc = false;
			}
		}
	}

	function handleDelete() {
		if (confirmDelete) {
			dispatch('delete', { id: config.id });
		} else {
			confirmDelete = true;
		}
	}
</script>

<div class="card p-4 space-y-3">
	<div class="flex items-start justify-between gap-3">
		<div>
			<div class="flex items-center gap-2">
				<span class="font-semibold text-lg">{config.tax_year}</span>
				<span class="badge variant-ghost-primary text-xs">IRPF</span>
			</div>
			<p class="text-sm text-surface-400 mt-1">
				Bruto anual: <span class="text-surface-200 font-mono">{formatCurrency(config.gross_annual_salary)}</span>
			</p>
			{#if calculation}
				<p class="text-sm text-success-400 mt-1">
					Neto mensual: <span class="font-mono font-semibold">{formatCurrency(calculation.net_monthly)}</span>
					<span class="text-surface-400 ml-1">({(calculation.effective_rate * 100).toFixed(1)}% IRPF efectivo)</span>
				</p>
			{/if}
		</div>
		<div class="flex gap-1 flex-shrink-0">
			<button class="btn btn-sm variant-ghost-surface" on:click={() => dispatch('edit', { config })}>
				Editar
			</button>
			<button
				class="btn btn-sm"
				class:variant-ghost-error={!confirmDelete}
				class:variant-filled-error={confirmDelete}
				on:click={handleDelete}
			>
				{confirmDelete ? '¿Confirmar?' : 'Eliminar'}
			</button>
		</div>
	</div>

	<!-- Botón ver detalle -->
	<button
		class="btn btn-sm variant-ghost w-full text-sm"
		on:click={toggleDetail}
		disabled={loadingCalc}
	>
		{#if loadingCalc}
			Calculando…
		{:else}
			{showDetail ? '▲ Ocultar desglose' : '▼ Ver desglose fiscal'}
		{/if}
	</button>

	{#if showDetail && calculation}
		<div class="space-y-2 text-sm border-t border-surface-600 pt-3">
			<div class="grid grid-cols-2 gap-2">
				<div class="text-surface-400">Bruto anual</div>
				<div class="font-mono text-right">{formatCurrency(calculation.gross_annual)}</div>
				<div class="text-surface-400">Cotización SS ({(calculation.ss_rate * 100).toFixed(2)}%)</div>
				<div class="font-mono text-right text-error-400">−{formatCurrency(calculation.ss_annual)}</div>
				<div class="text-surface-400">Reducción trabajo</div>
				<div class="font-mono text-right text-success-400">−{formatCurrency(calculation.work_expenses_deduction)}</div>
				<div class="text-surface-400">Base imponible</div>
				<div class="font-mono text-right">{formatCurrency(calculation.taxable_base)}</div>
				<div class="text-surface-400">IRPF anual</div>
				<div class="font-mono text-right text-error-400">−{formatCurrency(calculation.irpf_annual)}</div>
				<div class="text-surface-400 font-semibold">Neto anual</div>
				<div class="font-mono text-right font-semibold text-success-400">{formatCurrency(calculation.net_annual)}</div>
				<div class="text-surface-400 font-semibold">Neto mensual</div>
				<div class="font-mono text-right font-semibold text-success-400">{formatCurrency(calculation.net_monthly)}</div>
			</div>

			{#if calculation.bracket_breakdown.length > 0}
				<div class="mt-3">
					<p class="text-surface-400 text-xs mb-2">Tramos IRPF aplicados:</p>
					<div class="space-y-1">
						{#each calculation.bracket_breakdown as bracket}
							<div class="flex justify-between text-xs">
								<span class="text-surface-300">{(bracket.rate * 100).toFixed(0)}% sobre {formatCurrency(bracket.taxable_in_bracket)}</span>
								<span class="font-mono text-error-400">−{formatCurrency(bracket.tax_in_bracket)}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>
