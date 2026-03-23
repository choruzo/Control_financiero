<script lang="ts">
	import { onMount } from 'svelte';
	import {
		transactionsStore,
		transactionsData,
		transactionsLoading,
		transactionsError,
		transactionsAccounts,
		transactionsCategories,
		transactionsFilters
	} from '$lib/stores/transactions';
	import TransactionFilters from '$lib/components/transactions/TransactionFilters.svelte';
	import TransactionRow from '$lib/components/transactions/TransactionRow.svelte';
	import TransactionForm from '$lib/components/transactions/TransactionForm.svelte';
	import CsvImportModal from '$lib/components/transactions/CsvImportModal.svelte';
	import type { TransactionItem, TransactionFilters as TxFilters } from '$lib/types';

	let showForm = false;
	let showCsvModal = false;
	let editingTransaction: TransactionItem | null = null;

	onMount(() => {
		transactionsStore.load();
	});

	function openNewForm() {
		editingTransaction = null;
		showForm = true;
	}

	function openEditForm(transaction: TransactionItem) {
		editingTransaction = transaction;
		showForm = true;
	}

	function handleFormSaved() {
		transactionsStore.refresh();
	}

	async function handleDelete(id: string) {
		try {
			await transactionsStore.deleteTransaction(id);
		} catch (e) {
			console.error('Error al eliminar:', e);
		}
	}

	async function handleCategoryChange(transaction: TransactionItem, categoryId: string) {
		try {
			await transactionsStore.updateCategory(transaction, categoryId);
		} catch (e) {
			console.error('Error al actualizar categoría:', e);
		}
	}

	function handleFiltersChange(newFilters: TxFilters) {
		transactionsStore.setFilters(newFilters);
	}

	function handleCsvImported() {
		showCsvModal = false;
		transactionsStore.refresh();
	}
</script>

<div class="space-y-4">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<h2 class="h3">Transacciones</h2>
		<div class="flex gap-2">
			<button
				type="button"
				class="btn btn-sm variant-soft"
				on:click={() => (showCsvModal = true)}
			>
				↑ Importar CSV
			</button>
			<button
				type="button"
				class="btn btn-sm variant-filled-primary"
				on:click={openNewForm}
			>
				+ Nueva transacción
			</button>
		</div>
	</div>

	<!-- Filtros -->
	<TransactionFilters
		filters={$transactionsFilters}
		accounts={$transactionsAccounts}
		categories={$transactionsCategories}
		on:change={(e) => handleFiltersChange(e.detail)}
	/>

	<!-- Error -->
	{#if $transactionsError}
		<div class="alert variant-filled-error p-4">
			{$transactionsError}
			<button
				type="button"
				class="btn btn-sm variant-soft ml-4"
				on:click={() => transactionsStore.refresh()}
			>
				Reintentar
			</button>
		</div>
	{/if}

	<!-- Tabla -->
	<div class="card overflow-hidden">
		{#if $transactionsLoading}
			<div class="p-8 text-center text-surface-400">
				<div class="animate-spin inline-block w-6 h-6 border-2 border-primary-500 border-t-transparent rounded-full mb-2"></div>
				<p>Cargando transacciones...</p>
			</div>
		{:else if $transactionsData && $transactionsData.items.length > 0}
			<div class="overflow-x-auto">
				<table class="table w-full">
					<thead>
						<tr class="bg-surface-700/50">
							<th class="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">
								Fecha
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">
								Descripción
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">
								Categoría
							</th>
							<th class="px-4 py-3 text-right text-xs font-medium text-surface-400 uppercase tracking-wider">
								Importe
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-surface-400 uppercase tracking-wider">
								Cuenta
							</th>
							<th class="px-4 py-3 text-right text-xs font-medium text-surface-400 uppercase tracking-wider">
								Acciones
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-surface-700/50">
						{#each $transactionsData.items as transaction (transaction.id)}
							<TransactionRow
								{transaction}
								accounts={$transactionsAccounts}
								categories={$transactionsCategories}
								on:delete={(e) => handleDelete(e.detail.id)}
								on:categoryChange={(e) =>
									handleCategoryChange(e.detail.transaction, e.detail.categoryId)}
								on:edit={(e) => openEditForm(e.detail.transaction)}
							/>
						{/each}
					</tbody>
				</table>
			</div>

			<!-- Paginación -->
			{#if $transactionsData.pages > 1}
				<div class="flex items-center justify-between px-4 py-3 border-t border-surface-700/50">
					<span class="text-sm text-surface-400">
						Mostrando {($transactionsData.page - 1) * $transactionsData.per_page + 1}–{Math.min(
							$transactionsData.page * $transactionsData.per_page,
							$transactionsData.total
						)} de {$transactionsData.total}
					</span>
					<div class="flex items-center gap-2">
						<button
							type="button"
							class="btn btn-sm variant-soft"
							disabled={$transactionsData.page <= 1}
							on:click={() => transactionsStore.changePage($transactionsData!.page - 1)}
						>
							← Anterior
						</button>

						{#each Array.from({ length: Math.min($transactionsData.pages, 5) }, (_, i) => {
							// Mostrar páginas alrededor de la actual
							const current = $transactionsData!.page;
							const total = $transactionsData!.pages;
							let start = Math.max(1, current - 2);
							const end = Math.min(total, start + 4);
							start = Math.max(1, end - 4);
							return start + i;
						}) as pageNum}
							<button
								type="button"
								class="btn btn-sm {pageNum === $transactionsData.page
									? 'variant-filled-primary'
									: 'variant-soft'}"
								on:click={() => transactionsStore.changePage(pageNum)}
							>
								{pageNum}
							</button>
						{/each}

						<button
							type="button"
							class="btn btn-sm variant-soft"
							disabled={$transactionsData.page >= $transactionsData.pages}
							on:click={() => transactionsStore.changePage($transactionsData!.page + 1)}
						>
							Siguiente →
						</button>
					</div>
				</div>
			{/if}

		{:else if $transactionsData && $transactionsData.items.length === 0}
			<div class="p-12 text-center text-surface-400">
				<div class="text-4xl mb-3">📋</div>
				<p class="text-lg mb-1">No hay transacciones</p>
				<p class="text-sm">Crea tu primera transacción o importa un CSV.</p>
			</div>
		{/if}
	</div>
</div>

<!-- Modales -->
<TransactionForm
	show={showForm}
	accounts={$transactionsAccounts}
	categories={$transactionsCategories}
	transaction={editingTransaction}
	on:close={() => (showForm = false)}
	on:saved={handleFormSaved}
/>

<CsvImportModal
	show={showCsvModal}
	accounts={$transactionsAccounts}
	on:close={() => (showCsvModal = false)}
	on:imported={handleCsvImported}
/>
