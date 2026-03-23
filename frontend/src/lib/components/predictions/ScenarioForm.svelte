<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { ScenarioRequest, RecurringExpenseModification } from '$lib/types';

	export let loading: boolean = false;

	const dispatch = createEventDispatcher<{ submit: ScenarioRequest }>();

	let name = '';
	let months_ahead = 6;
	let salary_variation_pct = 0;
	let euribor_variation_pct = 0;
	let gross_annual: number | null = null;
	let tax_year = 2026;
	let monte_carlo_simulations = 1000;
	let expenses: RecurringExpenseModification[] = [];

	function addExpense() {
		expenses = [...expenses, { description: '', monthly_amount: 0, action: 'add' }];
	}

	function removeExpense(index: number) {
		expenses = expenses.filter((_, i) => i !== index);
	}

	function handleSubmit() {
		const request: ScenarioRequest = {
			months_ahead,
			salary_variation_pct: salary_variation_pct !== 0 ? salary_variation_pct : undefined,
			euribor_variation_pct: euribor_variation_pct !== 0 ? euribor_variation_pct : undefined,
			monte_carlo_simulations
		};
		if (name.trim()) request.name = name.trim();
		if (gross_annual !== null && gross_annual > 0) {
			request.gross_annual = gross_annual;
			request.tax_year = tax_year;
		}
		const validExpenses = expenses.filter((e) => e.description.trim() && e.monthly_amount > 0);
		if (validExpenses.length > 0) request.recurring_expense_modifications = validExpenses;

		dispatch('submit', request);
	}
</script>

<div class="card p-5 bg-surface-700 space-y-5">
	<h3 class="font-semibold text-surface-100">Configurar escenario</h3>

	<!-- Nombre opcional -->
	<div class="space-y-1">
		<label class="text-sm text-surface-300" for="scenario-name">Nombre del escenario (opcional)</label>
		<input
			id="scenario-name"
			type="text"
			bind:value={name}
			placeholder="Ej. Aumento de sueldo 10%"
			class="input variant-form-material w-full"
		/>
	</div>

	<!-- Meses a simular -->
	<div class="space-y-1">
		<label class="text-sm text-surface-300" for="months-ahead">Meses a simular: <span class="text-primary-400 font-medium">{months_ahead}</span></label>
		<input
			id="months-ahead"
			type="range"
			min="1"
			max="24"
			step="1"
			bind:value={months_ahead}
			class="w-full accent-primary-500"
		/>
		<div class="flex justify-between text-xs text-surface-500">
			<span>1 mes</span><span>24 meses</span>
		</div>
	</div>

	<!-- Variación de sueldo -->
	<div class="space-y-1">
		<label class="text-sm text-surface-300" for="salary-slider">
			Variación de sueldo:
			<span class:text-green-400={salary_variation_pct > 0} class:text-red-400={salary_variation_pct < 0} class:text-surface-400={salary_variation_pct === 0} class="font-medium">
				{salary_variation_pct > 0 ? '+' : ''}{salary_variation_pct}%
			</span>
		</label>
		<input
			id="salary-slider"
			type="range"
			min="-50"
			max="100"
			step="1"
			bind:value={salary_variation_pct}
			class="w-full accent-primary-500"
		/>
		<div class="flex justify-between text-xs text-surface-500">
			<span>-50%</span><span>0%</span><span>+100%</span>
		</div>
	</div>

	<!-- Variación Euríbor -->
	<div class="space-y-1">
		<label class="text-sm text-surface-300" for="euribor-slider">
			Variación Euríbor:
			<span class:text-green-400={euribor_variation_pct < 0} class:text-red-400={euribor_variation_pct > 0} class:text-surface-400={euribor_variation_pct === 0} class="font-medium">
				{euribor_variation_pct > 0 ? '+' : ''}{euribor_variation_pct.toFixed(1)} pp
			</span>
		</label>
		<input
			id="euribor-slider"
			type="range"
			min="-2"
			max="5"
			step="0.1"
			bind:value={euribor_variation_pct}
			class="w-full accent-primary-500"
		/>
		<div class="flex justify-between text-xs text-surface-500">
			<span>-2 pp</span><span>0</span><span>+5 pp</span>
		</div>
	</div>

	<!-- Gastos recurrentes -->
	<div class="space-y-2">
		<div class="flex items-center justify-between">
			<span class="text-sm text-surface-300">Gastos recurrentes</span>
			<button type="button" class="btn btn-sm variant-ghost-primary" on:click={addExpense}>
				+ Añadir
			</button>
		</div>
		{#each expenses as expense, i}
			<div class="flex gap-2 items-center">
				<input
					type="text"
					bind:value={expense.description}
					placeholder="Descripción"
					class="input variant-form-material flex-1 text-sm"
				/>
				<input
					type="number"
					bind:value={expense.monthly_amount}
					min="0"
					step="0.01"
					placeholder="€/mes"
					class="input variant-form-material w-24 text-sm"
				/>
				<select bind:value={expense.action} class="select variant-form-material w-28 text-sm">
					<option value="add">Añadir</option>
					<option value="remove">Quitar</option>
				</select>
				<button
					type="button"
					class="btn btn-sm variant-ghost-error"
					on:click={() => removeExpense(i)}
					aria-label="Eliminar gasto"
				>✕</button>
			</div>
		{/each}
	</div>

	<!-- Cálculo IRPF opcional -->
	<details class="text-sm">
		<summary class="cursor-pointer text-surface-400 hover:text-surface-200 transition-colors">Impacto fiscal (opcional)</summary>
		<div class="mt-3 space-y-3 pl-2 border-l-2 border-surface-600">
			<div class="space-y-1">
				<label class="text-sm text-surface-300" for="gross-annual">Salario bruto anual (€)</label>
				<input
					id="gross-annual"
					type="number"
					bind:value={gross_annual}
					min="0"
					step="100"
					placeholder="Ej. 45000"
					class="input variant-form-material w-full"
				/>
			</div>
			<div class="space-y-1">
				<label class="text-sm text-surface-300" for="tax-year">Año fiscal</label>
				<select id="tax-year" bind:value={tax_year} class="select variant-form-material">
					<option value={2025}>2025</option>
					<option value={2026}>2026</option>
				</select>
			</div>
		</div>
	</details>

	<!-- Simulaciones Monte Carlo -->
	<div class="space-y-1">
		<label class="text-sm text-surface-300" for="mc-sims">Simulaciones Monte Carlo</label>
		<select id="mc-sims" bind:value={monte_carlo_simulations} class="select variant-form-material">
			<option value={500}>500 (rápido)</option>
			<option value={1000}>1.000 (recomendado)</option>
			<option value={2000}>2.000 (preciso)</option>
			<option value={5000}>5.000 (muy preciso)</option>
		</select>
	</div>

	<button
		type="button"
		class="btn variant-filled-primary w-full"
		on:click={handleSubmit}
		disabled={loading}
	>
		{#if loading}
			<span class="animate-spin mr-2">⟳</span> Analizando...
		{:else}
			Analizar escenario
		{/if}
	</button>
</div>
