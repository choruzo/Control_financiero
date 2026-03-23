<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type {
		InvestmentResponse,
		InvestmentCreate,
		InvestmentUpdate,
		AccountResponse,
		InvestmentType,
		InterestType,
		CompoundingFrequency
	} from '$lib/types';

	export let show = false;
	export let investment: InvestmentResponse | null = null;
	export let accounts: AccountResponse[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
		saved: { investment: InvestmentResponse };
	}>();

	$: isEditing = investment !== null;
	$: title = isEditing ? 'Editar inversión' : 'Nueva inversión';

	let name = '';
	let investmentType: InvestmentType = 'deposit';
	let principalAmount = '';
	let interestRate = '';
	let interestType: InterestType = 'simple';
	let compoundingFrequency: CompoundingFrequency = 'annually';
	let startDate = '';
	let maturityDate = '';
	let autoRenew = false;
	let renewalPeriodMonths = '';
	let currentValue = '';
	let accountId = '';
	let notes = '';
	let isSaving = false;
	let error = '';

	$: if (show) {
		if (investment) {
			name = investment.name;
			investmentType = investment.investment_type;
			principalAmount = String(investment.principal_amount);
			interestRate = String(investment.interest_rate);
			interestType = investment.interest_type;
			compoundingFrequency = investment.compounding_frequency ?? 'annually';
			startDate = investment.start_date;
			maturityDate = investment.maturity_date ?? '';
			autoRenew = investment.auto_renew;
			renewalPeriodMonths = investment.renewal_period_months ? String(investment.renewal_period_months) : '';
			currentValue = investment.current_value ? String(investment.current_value) : '';
			accountId = investment.account_id ?? '';
			notes = investment.notes ?? '';
		} else {
			name = '';
			investmentType = 'deposit';
			principalAmount = '';
			interestRate = '';
			interestType = 'simple';
			compoundingFrequency = 'annually';
			startDate = new Date().toISOString().slice(0, 10);
			maturityDate = '';
			autoRenew = false;
			renewalPeriodMonths = '';
			currentValue = '';
			accountId = '';
			notes = '';
		}
		error = '';
	}

	async function handleSubmit() {
		if (!name.trim()) { error = 'El nombre es obligatorio'; return; }
		const principal = parseFloat(principalAmount);
		if (isNaN(principal) || principal <= 0) { error = 'El capital debe ser mayor que cero'; return; }
		const rate = parseFloat(interestRate);
		if (isNaN(rate) || rate < 0) { error = 'La tasa debe ser un número >= 0'; return; }
		if (!startDate) { error = 'La fecha de inicio es obligatoria'; return; }
		if (maturityDate && maturityDate <= startDate) { error = 'El vencimiento debe ser posterior al inicio'; return; }
		if (autoRenew && !renewalPeriodMonths) { error = 'Indica los meses de renovación'; return; }

		isSaving = true;
		error = '';

		try {
			const { createInvestment, updateInvestment } = await import('$lib/api/investments');
			let saved: InvestmentResponse;

			if (isEditing && investment) {
				const updateData: InvestmentUpdate = {
					name: name.trim(),
					interest_rate: rate,
					maturity_date: maturityDate || undefined,
					auto_renew: autoRenew,
					renewal_period_months: renewalPeriodMonths ? parseInt(renewalPeriodMonths) : undefined,
					current_value: currentValue ? parseFloat(currentValue) : undefined,
					notes: notes.trim() || undefined
				};
				saved = await updateInvestment(investment.id, updateData);
			} else {
				const createData: InvestmentCreate = {
					name: name.trim(),
					investment_type: investmentType,
					principal_amount: principal,
					interest_rate: rate,
					interest_type: interestType,
					start_date: startDate
				};
				if (interestType === 'compound') createData.compounding_frequency = compoundingFrequency;
				if (maturityDate) createData.maturity_date = maturityDate;
				if (autoRenew) {
					createData.auto_renew = true;
					createData.renewal_period_months = parseInt(renewalPeriodMonths);
				}
				if (currentValue) createData.current_value = parseFloat(currentValue);
				if (accountId) createData.account_id = accountId;
				if (notes.trim()) createData.notes = notes.trim();
				saved = await createInvestment(createData);
			}

			dispatch('saved', { investment: saved });
			dispatch('close');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Error al guardar la inversión';
		} finally {
			isSaving = false;
		}
	}
</script>

{#if show}
	<div
		class="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4"
		role="dialog"
		aria-modal="true"
		aria-label={title}
	>
		<div class="card w-full max-w-lg bg-surface-800 shadow-xl z-50 max-h-[90vh] overflow-y-auto" on:click|stopPropagation>
			<header class="card-header flex items-center justify-between sticky top-0 bg-surface-800 z-10">
				<h3 class="h3">{title}</h3>
				<button
					class="btn btn-sm variant-ghost-surface"
					on:click={() => dispatch('close')}
					disabled={isSaving}
					aria-label="Cerrar"
				>
					✕
				</button>
			</header>

			<form on:submit|preventDefault={handleSubmit} class="p-4 space-y-4">
				<!-- Nombre -->
				<label class="label">
					<span>Nombre <span class="text-error-400">*</span></span>
					<input
						type="text"
						class="input"
						placeholder="Ej: Depósito Banco X 2025"
						bind:value={name}
						maxlength="100"
						required
					/>
				</label>

				<!-- Tipo (solo en creación) -->
				{#if !isEditing}
					<label class="label">
						<span>Tipo <span class="text-error-400">*</span></span>
						<select class="select" bind:value={investmentType}>
							<option value="deposit">Depósito</option>
							<option value="fund">Fondo</option>
							<option value="stock">Acciones</option>
							<option value="bond">Bono</option>
						</select>
					</label>
				{/if}

				<!-- Capital (solo en creación) -->
				{#if !isEditing}
					<label class="label">
						<span>Capital inicial (€) <span class="text-error-400">*</span></span>
						<input
							type="number"
							class="input"
							placeholder="0.00"
							bind:value={principalAmount}
							min="0.01"
							step="0.01"
							required
						/>
					</label>
				{/if}

				<!-- Tasa anual -->
				<label class="label">
					<span>Tasa anual (%) <span class="text-error-400">*</span></span>
					<input
						type="number"
						class="input"
						placeholder="0.00"
						bind:value={interestRate}
						min="0"
						step="0.01"
						required
					/>
				</label>

				<!-- Tipo de interés (solo en creación) -->
				{#if !isEditing}
					<fieldset class="space-y-2">
						<legend class="text-sm font-medium text-surface-200">Tipo de interés</legend>
						<div class="flex gap-4">
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="radio" bind:group={interestType} value="simple" class="radio" />
								<span>Simple</span>
							</label>
							<label class="flex items-center gap-2 cursor-pointer">
								<input type="radio" bind:group={interestType} value="compound" class="radio" />
								<span>Compuesto</span>
							</label>
						</div>
					</fieldset>

					{#if interestType === 'compound'}
						<label class="label">
							<span>Frecuencia de capitalización <span class="text-error-400">*</span></span>
							<select class="select" bind:value={compoundingFrequency}>
								<option value="annually">Anual</option>
								<option value="quarterly">Trimestral</option>
								<option value="monthly">Mensual</option>
							</select>
						</label>
					{/if}
				{/if}

				<!-- Fechas -->
				<div class="grid grid-cols-2 gap-3">
					<label class="label">
						<span>Fecha inicio <span class="{isEditing ? 'text-surface-400' : 'text-error-400'}">*</span></span>
						<input
							type="date"
							class="input"
							bind:value={startDate}
							disabled={isEditing}
							required={!isEditing}
						/>
					</label>
					<label class="label">
						<span>Vencimiento <span class="text-surface-400 text-xs">(opcional)</span></span>
						<input
							type="date"
							class="input"
							bind:value={maturityDate}
							min={startDate}
						/>
					</label>
				</div>

				<!-- Renovación automática -->
				{#if maturityDate}
					<div class="space-y-2">
						<label class="flex items-center gap-2 cursor-pointer">
							<input type="checkbox" class="checkbox" bind:checked={autoRenew} />
							<span class="text-sm">Renovación automática al vencimiento</span>
						</label>
						{#if autoRenew}
							<label class="label ml-6">
								<span class="text-sm">Meses de renovación <span class="text-error-400">*</span></span>
								<input
									type="number"
									class="input"
									placeholder="12"
									bind:value={renewalPeriodMonths}
									min="1"
									max="360"
								/>
							</label>
						{/if}
					</div>
				{/if}

				<!-- Valor actual (opcional) -->
				<label class="label">
					<span>Valor actual (€) <span class="text-surface-400 text-xs">(opcional — para fondos/acciones)</span></span>
					<input
						type="number"
						class="input"
						placeholder="Dejar vacío para calcular automáticamente"
						bind:value={currentValue}
						min="0"
						step="0.01"
					/>
				</label>

				<!-- Cuenta asociada (solo en creación) -->
				{#if !isEditing && accounts.length > 0}
					<label class="label">
						<span>Cuenta asociada <span class="text-surface-400 text-xs">(opcional)</span></span>
						<select class="select" bind:value={accountId}>
							<option value="">-- Sin asociar --</option>
							{#each accounts as acc}
								<option value={acc.id}>{acc.name} ({acc.bank})</option>
							{/each}
						</select>
					</label>
				{/if}

				<!-- Notas -->
				<label class="label">
					<span>Notas <span class="text-surface-400 text-xs">(opcional)</span></span>
					<textarea
						class="textarea"
						rows="2"
						placeholder="Información adicional..."
						bind:value={notes}
						maxlength="1000"
					></textarea>
				</label>

				{#if error}
					<div class="alert variant-filled-error text-sm">{error}</div>
				{/if}

				<div class="flex justify-end gap-3 pt-2">
					<button
						type="button"
						class="btn variant-ghost-surface"
						on:click={() => dispatch('close')}
						disabled={isSaving}
					>
						Cancelar
					</button>
					<button type="submit" class="btn variant-filled-primary" disabled={isSaving}>
						{isSaving ? 'Guardando...' : isEditing ? 'Guardar cambios' : 'Crear inversión'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}
