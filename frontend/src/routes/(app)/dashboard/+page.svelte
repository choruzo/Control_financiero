<script lang="ts">
	import { onMount } from 'svelte';
	import { dashboardStore, dashboardData, dashboardLoading, dashboardError } from '$lib/stores/dashboard';
	import KpiCard from '$lib/components/dashboard/KpiCard.svelte';
	import CashflowChart from '$lib/components/dashboard/CashflowChart.svelte';
	import ExpensesPieChart from '$lib/components/dashboard/ExpensesPieChart.svelte';
	import BudgetAlertsWidget from '$lib/components/dashboard/BudgetAlertsWidget.svelte';
	import RecentTransactionsWidget from '$lib/components/dashboard/RecentTransactionsWidget.svelte';

	const now = new Date();
	const currentYear = now.getFullYear();
	const currentMonth = now.getMonth() + 1;

	const monthNames = [
		'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
		'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
	];
	$: monthLabel = `${monthNames[currentMonth - 1]} ${currentYear}`;

	onMount(() => {
		dashboardStore.load(currentYear, currentMonth);
	});

	async function handleMarkRead(event: CustomEvent<string>) {
		await dashboardStore.markAlertRead(event.detail);
	}
</script>

<svelte:head>
	<title>Dashboard — FinControl</title>
</svelte:head>

<div class="space-y-6">
	<!-- Cabecera -->
	<header class="flex items-center justify-between">
		<div>
			<h1 class="h2 font-bold">Dashboard</h1>
			<p class="text-surface-400 text-sm">{monthLabel}</p>
		</div>
		{#if !$dashboardLoading && $dashboardData}
			<button
				class="btn btn-sm variant-ghost-surface"
				on:click={() => dashboardStore.refresh(currentYear, currentMonth)}
			>
				↻ Actualizar
			</button>
		{/if}
	</header>

	<!-- Mensaje de error crítico -->
	{#if $dashboardError}
		<aside class="card p-4 variant-filled-error" role="alert">
			<p class="text-sm font-medium">⚠ {$dashboardError}</p>
		</aside>
	{/if}

	<!-- KPI Cards -->
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
		<KpiCard
			label="Balance total"
			icon="💰"
			value={$dashboardData?.overview.total_balance ?? null}
			formatAs="currency"
			loading={$dashboardLoading}
		/>
		<KpiCard
			label="Ingresos del mes"
			icon="📥"
			value={$dashboardData?.overview.total_income ?? null}
			formatAs="currency"
			loading={$dashboardLoading}
		/>
		<KpiCard
			label="Gastos del mes"
			icon="📤"
			value={$dashboardData?.overview.total_expenses ?? null}
			formatAs="currency"
			loading={$dashboardLoading}
		/>
		<KpiCard
			label="Tasa de ahorro"
			icon="🏦"
			value={$dashboardData?.overview.savings_rate ?? null}
			formatAs="percent"
			loading={$dashboardLoading}
		/>
	</div>

	<!-- Gráficos -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
		<CashflowChart
			data={$dashboardData?.cashflow ?? []}
			loading={$dashboardLoading}
		/>
		<ExpensesPieChart
			data={$dashboardData?.expensesByCategory ?? []}
			loading={$dashboardLoading}
		/>
	</div>

	<!-- Widgets inferiores -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
		<BudgetAlertsWidget
			alerts={$dashboardData?.budgetAlerts ?? []}
			loading={$dashboardLoading}
			on:markRead={handleMarkRead}
		/>
		<RecentTransactionsWidget
			transactions={$dashboardData?.recentTransactions ?? []}
			loading={$dashboardLoading}
		/>
	</div>
</div>
