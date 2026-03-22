<script lang="ts">
	import { currentUser } from '$lib/stores/auth';

	const kpiCards = [
		{ label: 'Balance total', icon: '💰' },
		{ label: 'Ingresos mes', icon: '📥' },
		{ label: 'Gastos mes', icon: '📤' },
		{ label: 'Tasa de ahorro', icon: '🏦' }
	];
</script>

<svelte:head>
	<title>Dashboard — FinControl</title>
</svelte:head>

<div class="space-y-6">
	<header>
		<h1 class="h2 font-bold">Dashboard</h1>
		<p class="text-surface-400">
			Bienvenido, <span class="text-primary-400">{$currentUser?.email ?? 'usuario'}</span>
		</p>
	</header>

	<!-- KPI Cards (placeholder hasta Fase 5.2) -->
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
		{#each kpiCards as card}
			<div class="card p-4 bg-surface-700 space-y-2">
				<div class="flex items-center justify-between">
					<p class="text-surface-400 text-sm">{card.label}</p>
					<span class="text-xl">{card.icon}</span>
				</div>
				<p class="text-2xl font-bold text-primary-400">—</p>
				<p class="text-surface-500 text-xs">Disponible en Fase 5.2</p>
			</div>
		{/each}
	</div>

	<!-- Área de gráficos (placeholder) -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
		<div class="card p-6 bg-surface-700 h-48 flex items-center justify-center">
			<p class="text-surface-500 text-sm text-center">
				Gráfico de cash flow mensual<br />
				<span class="text-xs">(Fase 5.2)</span>
			</p>
		</div>
		<div class="card p-6 bg-surface-700 h-48 flex items-center justify-center">
			<p class="text-surface-500 text-sm text-center">
				Gastos por categoría<br />
				<span class="text-xs">(Fase 5.2)</span>
			</p>
		</div>
	</div>
</div>
