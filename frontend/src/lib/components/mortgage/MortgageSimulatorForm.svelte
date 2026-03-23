<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { mortgageStore, mortgageCurrentResult, mortgageCalculating } from '$lib/stores/mortgage';
	import { formatCurrency, formatPercent } from '$lib/utils/format';
	import type { MortgageRateType, MortgageReviewFrequency, MortgagePropertyType } from '$lib/types';

	const dispatch = createEventDispatcher<{ saved: void }>();

	// ── Inmueble ──────────────────────────────────────────────────────────────
	let propertyPrice = 300000;
	let downPayment = 60000;

	$: loanAmount = Math.max(0, propertyPrice - downPayment);
	$: ltv = propertyPrice > 0 ? (loanAmount / propertyPrice) * 100 : 0;

	// ── Tipo de hipoteca ──────────────────────────────────────────────────────
	let rateType: MortgageRateType = 'fixed';
	const rateTypes: { value: MortgageRateType; label: string }[] = [
		{ value: 'fixed', label: 'Fijo' },
		{ value: 'variable', label: 'Variable' },
		{ value: 'mixed', label: 'Mixto' }
	];

	// Fijo
	let interestRate = 3.5;

	// Variable / Mixto
	let euriborRate = 3.5;
	let spread = 0.8;
	let reviewFrequency: MortgageReviewFrequency = 'annual';

	// Mixto
	let fixedYears = 5;

	// ── Plazo ─────────────────────────────────────────────────────────────────
	let termYears = 30;

	// ── Gastos ───────────────────────────────────────────────────────────────
	let includeCosts = true;
	let propertyType: MortgagePropertyType = 'second_hand';

	// ── Guardar ──────────────────────────────────────────────────────────────
	let showSaveModal = false;
	let saveName = '';
	let isSaving = false;
	let saveError = '';

	// ── Errores ───────────────────────────────────────────────────────────────
	let formError = '';

	function validateForm(): boolean {
		if (propertyPrice <= 0) { formError = 'El precio debe ser mayor que 0'; return false; }
		if (downPayment <= 0) { formError = 'La entrada debe ser mayor que 0'; return false; }
		if (downPayment >= propertyPrice) { formError = 'La entrada debe ser menor que el precio'; return false; }
		if (rateType === 'fixed' && interestRate <= 0) { formError = 'Indica el tipo de interés fijo'; return false; }
		if ((rateType === 'variable' || rateType === 'mixed') && spread < 0) { formError = 'El diferencial no puede ser negativo'; return false; }
		if (rateType === 'mixed' && fixedYears >= termYears) { formError = 'Los años fijos deben ser menores que el plazo total'; return false; }
		formError = '';
		return true;
	}

	async function handleCalculate() {
		if (!validateForm()) return;

		const data = buildRequest();
		try {
			await mortgageStore.simulate(data);
		} catch {
			// error ya en el store
		}
	}

	function buildRequest() {
		const base = {
			property_price: propertyPrice,
			down_payment: downPayment,
			rate_type: rateType,
			term_years: termYears,
			include_costs: includeCosts,
			property_type: propertyType
		};

		if (rateType === 'fixed') return { ...base, interest_rate: interestRate };
		if (rateType === 'variable') return { ...base, euribor_rate: euriborRate, spread, review_frequency: reviewFrequency };
		return { ...base, interest_rate: interestRate, euribor_rate: euriborRate, spread, fixed_years: fixedYears, review_frequency: reviewFrequency };
	}

	async function handleSave() {
		if (!saveName.trim()) { saveError = 'El nombre es obligatorio'; return; }
		if (!validateForm()) { showSaveModal = false; return; }
		isSaving = true;
		saveError = '';
		try {
			await mortgageStore.saveSimulation({ ...buildRequest(), name: saveName.trim() });
			showSaveModal = false;
			saveName = '';
			dispatch('saved');
		} catch (err) {
			saveError = err instanceof Error ? err.message : 'Error al guardar';
		} finally {
			isSaving = false;
		}
	}
</script>

<div class="card p-4 bg-surface-700 space-y-5">
	<h3 class="text-base font-semibold text-surface-100">Datos de la hipoteca</h3>

	<!-- Inmueble -->
	<div class="space-y-3">
		<p class="text-xs font-medium text-surface-400 uppercase tracking-wide">Inmueble</p>
		<div class="grid grid-cols-2 gap-3">
			<label class="label">
				<span class="text-sm text-surface-300">Precio (€)</span>
				<input class="input" type="number" min="1" step="1000" bind:value={propertyPrice} />
			</label>
			<label class="label">
				<span class="text-sm text-surface-300">Entrada (€)</span>
				<input class="input" type="number" min="1" step="1000" bind:value={downPayment} />
			</label>
		</div>
		<div class="flex gap-4 text-sm">
			<span class="text-surface-400">Préstamo: <span class="text-surface-100 font-medium">{formatCurrency(loanAmount)}</span></span>
			<span class="text-surface-400">LTV: <span class="{ltv > 80 ? 'text-warning-400' : 'text-success-400'} font-medium">{formatPercent(ltv)}</span></span>
		</div>
	</div>

	<!-- Tipo de hipoteca -->
	<div class="space-y-3">
		<p class="text-xs font-medium text-surface-400 uppercase tracking-wide">Tipo de hipoteca</p>
		<div class="flex gap-2">
			{#each rateTypes as rt}
				<button
					type="button"
					class="btn btn-sm {rateType === rt.value ? 'variant-filled-primary' : 'variant-ghost-surface'}"
					on:click={() => (rateType = rt.value)}
				>
					{rt.label}
				</button>
			{/each}
		</div>

		{#if rateType === 'fixed'}
			<label class="label">
				<span class="text-sm text-surface-300">Tipo de interés fijo (%)</span>
				<input class="input" type="number" min="0" max="15" step="0.05" bind:value={interestRate} />
			</label>
		{:else if rateType === 'variable'}
			<div class="grid grid-cols-2 gap-3">
				<label class="label">
					<span class="text-sm text-surface-300">Euríbor actual (%)</span>
					<input class="input" type="number" min="0" max="10" step="0.05" bind:value={euriborRate} />
				</label>
				<label class="label">
					<span class="text-sm text-surface-300">Diferencial (%)</span>
					<input class="input" type="number" min="0" max="5" step="0.05" bind:value={spread} />
				</label>
			</div>
			<div class="text-sm text-surface-400">
				Tasa efectiva: <span class="text-surface-100 font-medium">{formatPercent(euriborRate + spread)}</span>
			</div>
		{:else}
			<div class="grid grid-cols-2 gap-3">
				<label class="label">
					<span class="text-sm text-surface-300">Tipo fijo inicial (%)</span>
					<input class="input" type="number" min="0" max="15" step="0.05" bind:value={interestRate} />
				</label>
				<label class="label">
					<span class="text-sm text-surface-300">Años período fijo</span>
					<input class="input" type="number" min="1" max={termYears - 1} step="1" bind:value={fixedYears} />
				</label>
				<label class="label">
					<span class="text-sm text-surface-300">Euríbor (%)</span>
					<input class="input" type="number" min="0" max="10" step="0.05" bind:value={euriborRate} />
				</label>
				<label class="label">
					<span class="text-sm text-surface-300">Diferencial (%)</span>
					<input class="input" type="number" min="0" max="5" step="0.05" bind:value={spread} />
				</label>
			</div>
		{/if}

		{#if rateType !== 'fixed'}
			<label class="label">
				<span class="text-sm text-surface-300">Revisión del tipo</span>
				<select class="select" bind:value={reviewFrequency}>
					<option value="annual">Anual</option>
					<option value="semiannual">Semestral</option>
				</select>
			</label>
		{/if}
	</div>

	<!-- Plazo -->
	<div class="space-y-2">
		<div class="flex justify-between items-center">
			<p class="text-xs font-medium text-surface-400 uppercase tracking-wide">Plazo</p>
			<span class="text-sm font-semibold text-surface-100">{termYears} años</span>
		</div>
		<input class="range" type="range" min="5" max="40" step="1" bind:value={termYears} />
		<div class="flex justify-between text-xs text-surface-500">
			<span>5 años</span>
			<span>40 años</span>
		</div>
	</div>

	<!-- Gastos -->
	<div class="space-y-2">
		<p class="text-xs font-medium text-surface-400 uppercase tracking-wide">Gastos de compraventa</p>
		<label class="flex items-center gap-2 cursor-pointer">
			<input class="checkbox" type="checkbox" bind:checked={includeCosts} />
			<span class="text-sm text-surface-300">Incluir gastos (notaría, registro, impuestos...)</span>
		</label>
		{#if includeCosts}
			<div class="flex gap-3">
				<label class="flex items-center gap-2 cursor-pointer">
					<input class="radio" type="radio" name="propertyType" value="second_hand" bind:group={propertyType} />
					<span class="text-sm text-surface-300">Segunda mano (ITP 8%)</span>
				</label>
				<label class="flex items-center gap-2 cursor-pointer">
					<input class="radio" type="radio" name="propertyType" value="new" bind:group={propertyType} />
					<span class="text-sm text-surface-300">Obra nueva (AJD 1%)</span>
				</label>
			</div>
		{/if}
	</div>

	<!-- Error -->
	{#if formError}
		<div class="alert variant-filled-error text-sm p-2">{formError}</div>
	{/if}

	<!-- Botones -->
	<div class="flex gap-3">
		<button
			type="button"
			class="btn variant-filled-primary flex-1"
			on:click={handleCalculate}
			disabled={$mortgageCalculating}
		>
			{$mortgageCalculating ? 'Calculando...' : 'Calcular'}
		</button>
		{#if $mortgageCurrentResult}
			<button
				type="button"
				class="btn variant-ghost-surface"
				on:click={() => { showSaveModal = true; saveName = ''; saveError = ''; }}
			>
				Guardar
			</button>
		{/if}
	</div>

	<!-- KPIs resultado inline -->
	{#if $mortgageCurrentResult}
		{@const r = $mortgageCurrentResult}
		<div class="grid grid-cols-2 gap-3 pt-2 border-t border-surface-600">
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Cuota mensual</p>
				<p class="text-lg font-bold text-primary-400">{formatCurrency(r.initial_monthly_payment)}</p>
			</div>
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Total pagado</p>
				<p class="text-base font-semibold text-surface-100">{formatCurrency(r.total_amount_paid)}</p>
			</div>
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">Total intereses</p>
				<p class="text-base font-semibold text-error-400">{formatCurrency(r.total_interest)}</p>
			</div>
			<div class="space-y-0.5">
				<p class="text-xs text-surface-400">TAE</p>
				<p class="text-base font-semibold text-surface-100">{formatPercent(r.effective_annual_rate)}</p>
			</div>
			{#if r.closing_costs}
				<div class="col-span-2 space-y-0.5">
					<p class="text-xs text-surface-400">Gastos cierre estimados</p>
					<p class="text-base font-semibold text-warning-400">{formatCurrency(r.closing_costs.total)}</p>
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Modal Guardar -->
{#if showSaveModal}
	<div class="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4">
		<div class="card w-full max-w-sm z-50 p-5 space-y-4 bg-surface-800">
			<div class="flex items-center justify-between">
				<h3 class="h4">Guardar simulación</h3>
				<button type="button" class="btn-icon variant-ghost-surface btn-sm" on:click={() => (showSaveModal = false)}>✕</button>
			</div>
			<label class="label">
				<span class="text-sm text-surface-300">Nombre</span>
				<input class="input" type="text" placeholder="Ej. Piso Malasaña 30 años fijo" bind:value={saveName} maxlength="150" />
			</label>
			{#if saveError}
				<div class="alert variant-filled-error text-sm p-2">{saveError}</div>
			{/if}
			<div class="flex justify-end gap-3">
				<button type="button" class="btn variant-ghost-surface" on:click={() => (showSaveModal = false)}>Cancelar</button>
				<button type="button" class="btn variant-filled-primary" on:click={handleSave} disabled={isSaving}>
					{isSaving ? 'Guardando...' : 'Guardar'}
				</button>
			</div>
		</div>
	</div>
{/if}
