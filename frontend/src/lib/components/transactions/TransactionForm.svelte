<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { TransactionItem, AccountResponse, CategoryResponse, TransactionCreate, TransactionUpdate } from '$lib/types';

	export let show = false;
	export let accounts: AccountResponse[] = [];
	export let categories: CategoryResponse[] = [];
	export let transaction: TransactionItem | null = null;

	const dispatch = createEventDispatcher<{
		close: void;
		saved: { transaction: TransactionItem };
	}>();

	// Modos: crear o editar
	$: isEditing = transaction !== null;
	$: title = isEditing ? 'Editar transacción' : 'Nueva transacción';

	// Campos del formulario
	let accountId = '';
	let description = '';
	let amount = '';
	let transactionType: 'income' | 'expense' | 'transfer' = 'expense';
	let date = new Date().toISOString().split('T')[0];
	let categoryId = '';
	let isRecurring = false;
	let recurrenceRule: 'daily' | 'weekly' | 'monthly' | 'yearly' | '' = '';
	let notes = '';

	// Estado ML
	let mlSuggestedCategoryId = '';
	let mlConfidence = 0;
	let showMlBadge = false;

	// Estado del formulario
	let isSaving = false;
	let error = '';

	// Inicializar con los datos de la transacción a editar
	$: if (show) {
		if (transaction) {
			accountId = transaction.account_id;
			description = transaction.description;
			amount = String(Math.abs(transaction.amount));
			transactionType = transaction.transaction_type;
			date = transaction.date;
			categoryId = transaction.category_id ?? '';
			isRecurring = transaction.is_recurring;
			notes = '';
			showMlBadge = false;
		} else {
			// Limpiar para nueva transacción
			accountId = accounts[0]?.id ?? '';
			description = '';
			amount = '';
			transactionType = 'expense';
			date = new Date().toISOString().split('T')[0];
			categoryId = '';
			isRecurring = false;
			recurrenceRule = '';
			notes = '';
			showMlBadge = false;
			error = '';
		}
	}

	// Importar la función de transacciones dinámicamente para evitar dependencias circulares en tests
	async function handleDescriptionBlur() {
		if (!description.trim() || isEditing || categoryId) return;

		// Obtener sugerencia ML via el endpoint de predicción
		try {
			const { apiFetchJson } = await import('$lib/api/client');
			const result = await apiFetchJson<{
				category_id: string | null;
				confidence: number;
				status: string;
			}>('/api/v1/ml/predict', {
				method: 'POST',
				body: JSON.stringify({ description: description.trim() })
			});

			if (result.category_id && result.confidence > 0.5) {
				mlSuggestedCategoryId = result.category_id;
				mlConfidence = result.confidence;
				categoryId = result.category_id;
				showMlBadge = true;
			}
		} catch {
			// Sugerencia ML es best-effort
		}
	}

	async function handleSubmit() {
		if (!accountId || !description.trim() || !amount || !date) {
			error = 'Por favor completa todos los campos obligatorios.';
			return;
		}

		isSaving = true;
		error = '';

		try {
			const { createTransaction, updateTransaction } = await import('$lib/api/transactions');

			let saved: TransactionItem;

			if (isEditing && transaction) {
				const data: TransactionUpdate = {
					description: description.trim(),
					amount: parseFloat(amount),
					transaction_type: transactionType,
					date,
					category_id: categoryId || null,
					is_recurring: isRecurring,
					recurrence_rule: isRecurring && recurrenceRule ? recurrenceRule : null,
					notes: notes.trim() || undefined
				};
				saved = await updateTransaction(transaction.id, data);
			} else {
				const data: TransactionCreate = {
					account_id: accountId,
					description: description.trim(),
					amount: parseFloat(amount),
					transaction_type: transactionType,
					date,
					...(categoryId ? { category_id: categoryId } : {}),
					is_recurring: isRecurring,
					...(isRecurring && recurrenceRule ? { recurrence_rule: recurrenceRule } : {}),
					...(notes.trim() ? { notes: notes.trim() } : {})
				};
				saved = await createTransaction(data);
			}

			dispatch('saved', { transaction: saved });
			dispatch('close');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Error al guardar la transacción.';
		} finally {
			isSaving = false;
		}
	}

	function handleClose() {
		if (!isSaving) dispatch('close');
	}
</script>

{#if show}
	<!-- Overlay -->
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4"
		on:click|self={handleClose}
	>
		<div class="card w-full max-w-lg bg-surface-800 shadow-xl z-50 overflow-hidden">
			<!-- Header -->
			<header class="card-header flex items-center justify-between">
				<h3 class="h4">{title}</h3>
				<button
					type="button"
					class="btn btn-icon btn-sm variant-soft"
					on:click={handleClose}
					disabled={isSaving}
				>✕</button>
			</header>

			<!-- Formulario -->
			<form on:submit|preventDefault={handleSubmit} class="p-4 space-y-4">

				<!-- Cuenta -->
				<label class="label">
					<span>Cuenta <span class="text-error-400">*</span></span>
					<select class="select" bind:value={accountId} required>
						<option value="" disabled>Selecciona una cuenta</option>
						{#each accounts as acc}
							<option value={acc.id}>{acc.name} — {acc.bank}</option>
						{/each}
					</select>
				</label>

				<!-- Descripción -->
				<label class="label">
					<span>Descripción <span class="text-error-400">*</span></span>
					<input
						type="text"
						class="input"
						placeholder="Ej: MERCADONA SA"
						maxlength="255"
						bind:value={description}
						on:blur={handleDescriptionBlur}
						required
					/>
				</label>

				<!-- Importe + Tipo (en fila) -->
				<div class="grid grid-cols-2 gap-3">
					<label class="label">
						<span>Importe (€) <span class="text-error-400">*</span></span>
						<input
							type="number"
							class="input"
							placeholder="0.00"
							min="0.01"
							step="0.01"
							bind:value={amount}
							required
						/>
					</label>

					<label class="label">
						<span>Tipo <span class="text-error-400">*</span></span>
						<select class="select" bind:value={transactionType}>
							<option value="expense">Gasto</option>
							<option value="income">Ingreso</option>
							<option value="transfer">Transferencia</option>
						</select>
					</label>
				</div>

				<!-- Fecha -->
				<label class="label">
					<span>Fecha <span class="text-error-400">*</span></span>
					<input type="date" class="input" bind:value={date} required />
				</label>

				<!-- Categoría + badge ML -->
				<label class="label">
					<span class="flex items-center gap-2">
						Categoría
						{#if showMlBadge}
							<span class="badge variant-filled-warning text-xs">
								💡 Sugerida por IA ({Math.round(mlConfidence * 100)}%)
							</span>
						{/if}
					</span>
					<select class="select" bind:value={categoryId}>
						<option value="">Sin categoría</option>
						{#each categories as cat}
							<option value={cat.id}>{cat.name}</option>
						{/each}
					</select>
				</label>

				<!-- Recurrente -->
				<div class="flex items-center gap-4">
					<label class="flex items-center gap-2 cursor-pointer">
						<input type="checkbox" class="checkbox" bind:checked={isRecurring} />
						<span class="text-sm">Transacción recurrente</span>
					</label>

					{#if isRecurring}
						<select class="select select-sm flex-1" bind:value={recurrenceRule}>
							<option value="">Frecuencia...</option>
							<option value="daily">Diaria</option>
							<option value="weekly">Semanal</option>
							<option value="monthly">Mensual</option>
							<option value="yearly">Anual</option>
						</select>
					{/if}
				</div>

				<!-- Notas -->
				<label class="label">
					<span>Notas</span>
					<textarea
						class="textarea"
						placeholder="Opcional..."
						rows="2"
						bind:value={notes}
					></textarea>
				</label>

				<!-- Error -->
				{#if error}
					<div class="alert variant-filled-error text-sm p-3">{error}</div>
				{/if}

				<!-- Acciones -->
				<div class="flex justify-end gap-3 pt-2">
					<button
						type="button"
						class="btn variant-soft"
						on:click={handleClose}
						disabled={isSaving}
					>Cancelar</button>
					<button
						type="submit"
						class="btn variant-filled-primary"
						disabled={isSaving}
					>
						{#if isSaving}
							Guardando...
						{:else}
							{isEditing ? 'Guardar cambios' : 'Crear transacción'}
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}
