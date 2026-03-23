<script lang="ts">
	import { onMount } from 'svelte';
	import {
		investmentsStore,
		investmentsData,
		investmentsSummary,
		investmentsLoading,
		investmentsError,
		investmentsTypeFilter,
		investmentsMaturingSoon
	} from '$lib/stores/investments';
	import InvestmentCard from '$lib/components/investments/InvestmentCard.svelte';
	import InvestmentForm from '$lib/components/investments/InvestmentForm.svelte';
	import MaturityTimeline from '$lib/components/investments/MaturityTimeline.svelte';
	import { formatCurrency, formatPercent } from '$lib/utils/format';
	import type { InvestmentResponse, AccountResponse } from '$lib/types';

	let showForm = false;
	let editingInvestment: InvestmentResponse | null = null;
	let accounts: AccountResponse[] = [];

	const TYPE_FILTERS = [
		{ value: null, label: 'Todos' },
		{ value: 'deposit', label: 'Depósitos' },
		{ value: 'fund', label: 'Fondos' },
		{ value: 'stock', label: 'Acciones' },
		{ value: 'bond', label: 'Bonos' }
	] as const;

	const SKELETON_COUNT = 4;

	onMount(async () => {
		investmentsStore.load();
		// Cargar cuentas para el formulario
		try {
			const { getAccounts } = await import('$lib/api/accounts');
			accounts = await getAccounts();
		} catch {
			// best-effort
		}
	});

	function openNewForm() {
		editingInvestment = null;
		showForm = true;
	}

	function openEditForm(investment: InvestmentResponse) {
		editingInvestment = investment;
		showForm = true;
	}

	async function handleDelete(id: string) {
		try {
			await investmentsStore.deleteInvestment(id);
		} catch (e) {
			console.error('Error al eliminar inversión:', e);
		}
	}

	async function handleRenew(id: string) {
		try {
			await investmentsStore.renewInvestment(id);
		} catch (e) {
			console.error('Error al renovar inversión:', e);
		}
	}

	function handleFormSaved() {
		investmentsStore.load(true);
	}
</script>

<div class="space-y-6">
	<!-- Cabecera -->
	<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
		<h2 class="h3">Inversiones</h2>
		<button type="button" class="btn btn-sm variant-filled-primary" on:click={openNewForm}>
			+ Nueva inversión
		</button>
	</div>

	<!-- KPIs -->
	<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
		<!-- Total invertido -->
		<div class="card p-4 bg-surface-700 space-y-1">
			<p class="text-xs text-surface-400 uppercase tracking-wide">Capital total</p>
			{#if $investmentsLoading}
				<div class="animate-pulse h-6 bg-surface-600 rounded w-3/4"></div>
			{:else}
				<p class="text-xl font-semibold text-surface-100">
					{formatCurrency($investmentsSummary?.total_principal ?? 0)}
				</p>
			{/if}
		</div>

		<!-- Valor actual -->
		<div class="card p-4 bg-surface-700 space-y-1">
			<p class="text-xs text-surface-400 uppercase tracking-wide">Valor actual</p>
			{#if $investmentsLoading}
				<div class="animate-pulse h-6 bg-surface-600 rounded w-3/4"></div>
			{:else}
				<p class="text-xl font-semibold text-surface-100">
					{formatCurrency($investmentsSummary?.total_current_value ?? 0)}
				</p>
			{/if}
		</div>

		<!-- Rendimiento total -->
		<div class="card p-4 bg-surface-700 space-y-1">
			<p class="text-xs text-surface-400 uppercase tracking-wide">Rendimiento total</p>
			{#if $investmentsLoading}
				<div class="animate-pulse h-6 bg-surface-600 rounded w-3/4"></div>
			{:else}
				{@const ret = $investmentsSummary?.total_return ?? 0}
				{@const pct = $investmentsSummary?.average_return_percentage ?? 0}
				<p class="text-xl font-semibold {ret >= 0 ? 'text-success-400' : 'text-error-400'}">
					{formatCurrency(ret)}
				</p>
				<p class="text-xs {pct >= 0 ? 'text-success-500' : 'text-error-500'}">
					{formatPercent(pct)} promedio
				</p>
			{/if}
		</div>

		<!-- Nº inversiones activas -->
		<div class="card p-4 bg-surface-700 space-y-1">
			<p class="text-xs text-surface-400 uppercase tracking-wide">Inversiones activas</p>
			{#if $investmentsLoading}
				<div class="animate-pulse h-6 bg-surface-600 rounded w-1/2"></div>
			{:else}
				<p class="text-xl font-semibold text-surface-100">
					{$investmentsSummary?.total_investments ?? 0}
				</p>
				{#if $investmentsMaturingSoon.length > 0}
					<p class="text-xs text-warning-400">
						⏰ {$investmentsMaturingSoon.length} vence{$investmentsMaturingSoon.length > 1 ? 'n' : ''} pronto
					</p>
				{/if}
			{/if}
		</div>
	</div>

	<!-- Error -->
	{#if $investmentsError}
		<div class="alert variant-filled-error">
			<span>{$investmentsError}</span>
			<button
				class="btn btn-sm variant-ghost-surface ml-auto"
				on:click={() => investmentsStore.load(true)}
			>
				Reintentar
			</button>
		</div>
	{/if}

	<!-- Filtros de tipo -->
	<div class="flex gap-2 flex-wrap">
		{#each TYPE_FILTERS as filter}
			<button
				class="btn btn-sm {$investmentsTypeFilter === filter.value
					? 'variant-filled-primary'
					: 'variant-ghost-surface'}"
				on:click={() => investmentsStore.setTypeFilter(filter.value)}
			>
				{filter.label}
				{#if filter.value !== null && $investmentsSummary?.by_type[filter.value]}
					<span class="badge-icon variant-filled ml-1 text-xs">
						{$investmentsSummary.by_type[filter.value]}
					</span>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Grid de inversiones -->
	{#if $investmentsLoading}
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each Array(SKELETON_COUNT) as _}
				<InvestmentCard
					investment={{
						id: '', user_id: '', account_id: null, name: '',
						investment_type: 'deposit', principal_amount: 0, interest_rate: 0,
						interest_type: 'simple', compounding_frequency: null, current_value: null,
						start_date: '', maturity_date: null, auto_renew: false,
						renewal_period_months: null, renewals_count: 0, notes: null,
						is_active: true, created_at: '', updated_at: ''
					}}
					loading={true}
				/>
			{/each}
		</div>
	{:else if $investmentsData.length === 0 && !$investmentsError}
		<div class="card p-12 text-center space-y-4 bg-surface-700">
			<p class="text-4xl">💰</p>
			<p class="text-lg font-medium text-surface-200">
				{$investmentsTypeFilter
					? 'No tienes inversiones de este tipo'
					: 'No tienes inversiones registradas'}
			</p>
			<p class="text-sm text-surface-400">
				Registra tus depósitos, fondos, acciones y bonos para hacer seguimiento del rendimiento.
			</p>
			<button type="button" class="btn variant-filled-primary" on:click={openNewForm}>
				Registrar primera inversión
			</button>
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
			{#each $investmentsData as investment (investment.id)}
				<InvestmentCard
					{investment}
					on:edit={(e) => openEditForm(e.detail.investment)}
					on:delete={(e) => handleDelete(e.detail.id)}
					on:renew={(e) => handleRenew(e.detail.id)}
				/>
			{/each}
		</div>
	{/if}

	<!-- Timeline de vencimientos -->
	{#if !$investmentsLoading && $investmentsData.some((inv) => inv.maturity_date)}
		<MaturityTimeline investments={$investmentsData} />
	{/if}
</div>

<!-- Modal crear/editar -->
<InvestmentForm
	show={showForm}
	investment={editingInvestment}
	{accounts}
	on:close={() => (showForm = false)}
	on:saved={handleFormSaved}
/>
