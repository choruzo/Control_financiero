<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { formatCurrency } from '$lib/utils/format';
	import type { TransactionItem, AccountResponse, CategoryResponse } from '$lib/types';

	export let transaction: TransactionItem;
	export let accounts: AccountResponse[] = [];
	export let categories: CategoryResponse[] = [];

	const dispatch = createEventDispatcher<{
		delete: { id: string };
		categoryChange: { transaction: TransactionItem; categoryId: string };
		edit: { transaction: TransactionItem };
	}>();

	$: account = accounts.find((a) => a.id === transaction.account_id);
	$: category = categories.find((c) => c.id === transaction.category_id);

	// Indicador ML
	$: isAutoAssigned =
		transaction.ml_confidence !== null &&
		transaction.ml_confidence !== undefined &&
		transaction.ml_confidence > 0.92 &&
		transaction.category_id === transaction.ml_suggested_category_id;

	$: isSuggested =
		!isAutoAssigned &&
		transaction.ml_suggested_category_id !== null &&
		transaction.ml_confidence !== null &&
		transaction.ml_confidence !== undefined &&
		transaction.ml_confidence > 0.5;

	// Formateo de fecha
	$: formattedDate = (() => {
		const d = new Date(transaction.date + 'T00:00:00');
		return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
	})();

	// Color del importe
	$: amountClass =
		transaction.transaction_type === 'income'
			? 'text-success-500 font-medium'
			: transaction.transaction_type === 'expense'
				? 'text-error-500 font-medium'
				: 'text-surface-400';

	$: amountSign =
		transaction.transaction_type === 'income'
			? '+'
			: transaction.transaction_type === 'expense'
				? '-'
				: '';

	// Edición inline de categoría
	let editingCategory = false;
	let selectedCategoryId = transaction.category_id ?? '';

	function startEditCategory() {
		selectedCategoryId = transaction.category_id ?? '';
		editingCategory = true;
	}

	function cancelEditCategory() {
		editingCategory = false;
	}

	function confirmCategoryChange() {
		if (selectedCategoryId && selectedCategoryId !== transaction.category_id) {
			dispatch('categoryChange', { transaction, categoryId: selectedCategoryId });
		}
		editingCategory = false;
	}

	function handleDelete() {
		if (confirm(`¿Eliminar la transacción "${transaction.description}"?`)) {
			dispatch('delete', { id: transaction.id });
		}
	}
</script>

<tr class="hover:bg-surface-700/30 transition-colors">
	<!-- Fecha -->
	<td class="px-4 py-3 text-sm text-surface-300 whitespace-nowrap">{formattedDate}</td>

	<!-- Descripción + badge ML -->
	<td class="px-4 py-3">
		<div class="flex items-center gap-2">
			<span class="text-sm truncate max-w-xs" title={transaction.description}>
				{transaction.description}
			</span>
			{#if isAutoAssigned}
				<span class="badge variant-filled-primary text-xs" title="Categorizado por IA">🤖 IA</span>
			{:else if isSuggested}
				<span class="badge variant-filled-warning text-xs" title="Sugerencia pendiente de confirmar">
					💡 Sugerida
				</span>
			{/if}
		</div>
	</td>

	<!-- Categoría (con edición inline) -->
	<td class="px-4 py-3">
		{#if editingCategory}
			<div class="flex items-center gap-1">
				<select
					class="select select-sm text-xs"
					bind:value={selectedCategoryId}
					on:keydown={(e) => e.key === 'Escape' && cancelEditCategory()}
				>
					<option value="">Sin categoría</option>
					{#each categories as cat}
						<option value={cat.id}>{cat.name}</option>
					{/each}
				</select>
				<button
					type="button"
					class="btn btn-icon btn-sm variant-filled-success"
					on:click={confirmCategoryChange}
					title="Confirmar"
				>✓</button>
				<button
					type="button"
					class="btn btn-icon btn-sm variant-soft"
					on:click={cancelEditCategory}
					title="Cancelar"
				>✕</button>
			</div>
		{:else}
			<button
				type="button"
				class="text-sm text-left hover:underline decoration-dashed"
				on:click={startEditCategory}
				title="Clic para editar categoría"
			>
				{category?.name ?? '—'}
			</button>
		{/if}
	</td>

	<!-- Importe -->
	<td class="px-4 py-3 text-right whitespace-nowrap">
		<span class={amountClass}>
			{amountSign}{formatCurrency(Math.abs(transaction.amount))}
		</span>
	</td>

	<!-- Cuenta -->
	<td class="px-4 py-3 text-sm text-surface-300">
		{account?.name ?? '—'}
	</td>

	<!-- Acciones -->
	<td class="px-4 py-3 text-right">
		<div class="flex items-center justify-end gap-1">
			<button
				type="button"
				class="btn btn-icon btn-sm variant-soft"
				on:click={() => dispatch('edit', { transaction })}
				title="Editar"
			>✏️</button>
			<button
				type="button"
				class="btn btn-icon btn-sm variant-soft-error"
				on:click={handleDelete}
				title="Eliminar"
			>🗑️</button>
		</div>
	</td>
</tr>
