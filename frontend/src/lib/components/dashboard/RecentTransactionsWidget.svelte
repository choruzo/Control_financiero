<script lang="ts">
	import { formatCurrency } from '$lib/utils/format';
	import type { TransactionItem } from '$lib/types';

	export let transactions: TransactionItem[] = [];
	export let loading: boolean = false;

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('es-ES', {
			day: '2-digit',
			month: 'short'
		});
	}

	function amountClass(type: TransactionItem['transaction_type']): string {
		if (type === 'income') return 'text-success-400 font-medium';
		if (type === 'expense') return 'text-error-400 font-medium';
		return 'text-surface-300 font-medium';
	}

	function amountPrefix(type: TransactionItem['transaction_type']): string {
		if (type === 'income') return '+';
		if (type === 'expense') return '-';
		return '';
	}
</script>

<div class="card p-4 bg-surface-700 space-y-3">
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-medium text-surface-300">Últimas transacciones</h3>
	</div>

	{#if loading}
		<div class="animate-pulse space-y-2">
			{#each [1, 2, 3, 4, 5] as _}
				<div class="h-10 bg-surface-600 rounded"></div>
			{/each}
		</div>
	{:else if transactions.length === 0}
		<div class="py-6 text-center">
			<p class="text-surface-500 text-sm">Sin transacciones registradas</p>
		</div>
	{:else}
		<ul class="divide-y divide-surface-600">
			{#each transactions as tx (tx.id)}
				<li class="flex items-center justify-between py-2 gap-2">
					<div class="min-w-0">
						<p class="text-sm text-surface-200 truncate max-w-[200px]">{tx.description}</p>
						<p class="text-xs text-surface-500">{formatDate(tx.date)}</p>
					</div>
					<span class={amountClass(tx.transaction_type)}>
						{amountPrefix(tx.transaction_type)}{formatCurrency(tx.amount)}
					</span>
				</li>
			{/each}
		</ul>
		<div class="text-right">
			<a href="/transactions" class="text-xs text-primary-400 hover:underline">
				Ver todas →
			</a>
		</div>
	{/if}
</div>
