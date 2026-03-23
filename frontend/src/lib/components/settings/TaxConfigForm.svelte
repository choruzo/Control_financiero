<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { TaxConfigResponse, TaxConfigCreate, TaxConfigUpdate } from '$lib/types';

	export let show = false;
	export let editingConfig: TaxConfigResponse | null = null;
	export let existingYears: number[] = [];

	const dispatch = createEventDispatcher<{
		save: { data: TaxConfigCreate | TaxConfigUpdate; id?: string };
		close: void;
	}>();

	let taxYear = new Date().getFullYear();
	let grossSalary = 0;
	let saving = false;
	let error = '';

	const availableYears = Array.from({ length: 11 }, (_, i) => 2020 + i);

	$: if (show) {
		if (editingConfig) {
			taxYear = editingConfig.tax_year;
			grossSalary = editingConfig.gross_annual_salary;
		} else {
			// Seleccionar primer año no usado
			const unusedYear = availableYears.find((y) => !existingYears.includes(y));
			taxYear = unusedYear ?? new Date().getFullYear();
			grossSalary = 0;
		}
		error = '';
	}

	async function handleSubmit() {
		if (grossSalary <= 0) {
			error = 'El sueldo bruto debe ser mayor que 0';
			return;
		}
		if (!editingConfig && existingYears.includes(taxYear)) {
			error = `Ya existe una configuración para ${taxYear}`;
			return;
		}
		saving = true;
		error = '';
		if (editingConfig) {
			dispatch('save', { data: { gross_annual_salary: grossSalary }, id: editingConfig.id });
		} else {
			dispatch('save', { data: { tax_year: taxYear, gross_annual_salary: grossSalary } });
		}
		saving = false;
	}
</script>

{#if show}
	<div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
		<div class="card bg-surface-800 shadow-xl p-6 w-full max-w-md space-y-4">
			<h3 class="font-semibold text-lg">
				{editingConfig ? `Editar configuración ${editingConfig.tax_year}` : 'Nueva configuración fiscal'}
			</h3>

			{#if error}
				<aside class="alert variant-ghost-error text-sm">{error}</aside>
			{/if}

			{#if !editingConfig}
				<label class="label">
					<span>Año fiscal</span>
					<select class="select" bind:value={taxYear}>
						{#each availableYears as year}
							<option value={year} disabled={existingYears.includes(year)}>
								{year}{existingYears.includes(year) ? ' (ya configurado)' : ''}
							</option>
						{/each}
					</select>
				</label>
			{/if}

			<label class="label">
				<span>Sueldo bruto anual (€)</span>
				<input
					class="input"
					type="number"
					step="100"
					min="0"
					bind:value={grossSalary}
					placeholder="35000"
				/>
				<small class="text-surface-400">
					Se calculará IRPF + SS para obtener tu neto mensual
				</small>
			</label>

			<div class="flex justify-end gap-2 pt-2">
				<button class="btn variant-ghost" on:click={() => dispatch('close')}>
					Cancelar
				</button>
				<button
					class="btn variant-filled-primary"
					on:click={handleSubmit}
					disabled={saving || grossSalary <= 0}
				>
					{saving ? 'Guardando…' : 'Guardar'}
				</button>
			</div>
		</div>
	</div>
{/if}
