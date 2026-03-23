<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { TransactionFilters, AccountResponse, CategoryResponse, TransactionType } from '$lib/types';

	export let filters: TransactionFilters = {};
	export let accounts: AccountResponse[] = [];
	export let categories: CategoryResponse[] = [];

	const dispatch = createEventDispatcher<{ change: TransactionFilters }>();

	let dateFrom = filters.date_from ?? '';
	let dateTo = filters.date_to ?? '';
	let categoryId = filters.category_id ?? '';
	let accountId = filters.account_id ?? '';
	let transactionType = filters.transaction_type ?? '';

	function apply() {
		const newFilters: TransactionFilters = { page: 1, per_page: filters.per_page ?? 50 };
		if (dateFrom) newFilters.date_from = dateFrom;
		if (dateTo) newFilters.date_to = dateTo;
		if (categoryId) newFilters.category_id = categoryId;
		if (accountId) newFilters.account_id = accountId;
		if (transactionType) newFilters.transaction_type = transactionType as TransactionType;
		dispatch('change', newFilters);
	}

	function clear() {
		dateFrom = '';
		dateTo = '';
		categoryId = '';
		accountId = '';
		transactionType = '';
		dispatch('change', { page: 1, per_page: filters.per_page ?? 50 });
	}

	const hasActiveFilters =
		dateFrom || dateTo || categoryId || accountId || transactionType;
</script>

<div class="card p-4 mb-4">
	<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 items-end">
		<!-- Fecha inicio -->
		<label class="label">
			<span class="text-xs text-surface-400">Desde</span>
			<input
				type="date"
				class="input input-sm"
				bind:value={dateFrom}
				on:change={apply}
			/>
		</label>

		<!-- Fecha fin -->
		<label class="label">
			<span class="text-xs text-surface-400">Hasta</span>
			<input
				type="date"
				class="input input-sm"
				bind:value={dateTo}
				on:change={apply}
			/>
		</label>

		<!-- Tipo -->
		<label class="label">
			<span class="text-xs text-surface-400">Tipo</span>
			<select class="select select-sm" bind:value={transactionType} on:change={apply}>
				<option value="">Todos</option>
				<option value="income">Ingresos</option>
				<option value="expense">Gastos</option>
				<option value="transfer">Transferencias</option>
			</select>
		</label>

		<!-- Categoría -->
		<label class="label">
			<span class="text-xs text-surface-400">Categoría</span>
			<select class="select select-sm" bind:value={categoryId} on:change={apply}>
				<option value="">Todas</option>
				{#each categories as cat}
					<option value={cat.id}>{cat.name}</option>
				{/each}
			</select>
		</label>

		<!-- Cuenta -->
		<label class="label">
			<span class="text-xs text-surface-400">Cuenta</span>
			<select class="select select-sm" bind:value={accountId} on:change={apply}>
				<option value="">Todas</option>
				{#each accounts as acc}
					<option value={acc.id}>{acc.name}</option>
				{/each}
			</select>
		</label>

		<!-- Limpiar -->
		<div>
			<button
				type="button"
				class="btn btn-sm variant-soft w-full"
				on:click={clear}
				disabled={!hasActiveFilters}
			>
				Limpiar filtros
			</button>
		</div>
	</div>
</div>
