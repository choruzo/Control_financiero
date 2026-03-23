<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { formatCurrency, formatPercent } from '$lib/utils/format';
	import type { InvestmentResponse, InvestmentStatusResponse } from '$lib/types';

	export let investment: InvestmentResponse;
	export let loading: boolean = false;

	const dispatch = createEventDispatcher<{
		edit: { investment: InvestmentResponse };
		delete: { id: string };
		renew: { id: string };
	}>();

	let confirmDelete = false;
	let status: InvestmentStatusResponse | null = null;
	let statusLoading = true;

	// Etiquetas de tipo
	const TYPE_LABELS: Record<string, string> = {
		deposit: 'Depósito',
		fund: 'Fondo',
		stock: 'Acciones',
		bond: 'Bono'
	};

	const TYPE_BADGE_CLASS: Record<string, string> = {
		deposit: 'variant-filled-primary',
		fund: 'variant-filled-success',
		stock: 'variant-filled-warning',
		bond: 'variant-filled-tertiary'
	};

	$: daysToMaturity =
		investment.maturity_date
			? Math.ceil(
					(new Date(investment.maturity_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
				)
			: null;

	$: maturingSoon = daysToMaturity !== null && daysToMaturity >= 0 && daysToMaturity <= 30;
	$: maturityPast = daysToMaturity !== null && daysToMaturity < 0;

	onMount(async () => {
		try {
			const { getInvestmentStatus } = await import('$lib/api/investments');
			status = await getInvestmentStatus(investment.id);
		} catch {
			// best-effort — no mostrar error en la card
		} finally {
			statusLoading = false;
		}
	});

	function handleDelete() {
		if (confirmDelete) {
			dispatch('delete', { id: investment.id });
			confirmDelete = false;
		} else {
			confirmDelete = true;
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('es-ES', {
			day: '2-digit',
			month: 'short',
			year: 'numeric'
		});
	}
</script>

<div class="card p-4 space-y-3">
	{#if loading}
		<!-- Skeleton -->
		<div class="animate-pulse space-y-3">
			<div class="h-4 bg-surface-600 rounded w-3/4"></div>
			<div class="h-3 bg-surface-600 rounded w-1/2"></div>
			<div class="h-3 bg-surface-700 rounded w-full"></div>
			<div class="h-3 bg-surface-600 rounded w-2/3"></div>
		</div>
	{:else}
		<!-- Cabecera -->
		<div class="flex items-start justify-between gap-2">
			<div class="flex items-center gap-2 flex-wrap min-w-0">
				<span class="font-medium text-surface-100 truncate">{investment.name}</span>
				<span class="badge text-xs {TYPE_BADGE_CLASS[investment.investment_type] ?? 'variant-filled'}">
					{TYPE_LABELS[investment.investment_type] ?? investment.investment_type}
				</span>
				{#if maturingSoon}
					<span class="badge variant-filled-warning text-xs">⏰ Vence pronto</span>
				{:else if maturityPast}
					<span class="badge variant-ghost-error text-xs">Vencido</span>
				{/if}
			</div>
		</div>

		<!-- Capital e interés -->
		<div class="grid grid-cols-2 gap-2 text-sm">
			<div>
				<p class="text-surface-400 text-xs">Capital</p>
				<p class="font-semibold text-surface-100">{formatCurrency(investment.principal_amount)}</p>
			</div>
			<div>
				<p class="text-surface-400 text-xs">Tasa anual</p>
				<p class="font-semibold text-surface-100">
					{investment.interest_rate.toFixed(2)}%
					<span class="text-surface-400 font-normal text-xs">
						({investment.interest_type === 'compound'
							? investment.compounding_frequency === 'monthly'
								? 'mensual'
								: investment.compounding_frequency === 'quarterly'
									? 'trim.'
									: 'anual'
							: 'simple'})
					</span>
				</p>
			</div>
		</div>

		<!-- Rendimiento -->
		<div class="grid grid-cols-2 gap-2 text-sm">
			<div>
				<p class="text-surface-400 text-xs">Rendimiento</p>
				{#if statusLoading}
					<div class="animate-pulse h-4 bg-surface-600 rounded w-20"></div>
				{:else if status}
					<p class="font-semibold {status.total_return >= 0 ? 'text-success-400' : 'text-error-400'}">
						{formatCurrency(status.total_return)}
						<span class="text-xs">({formatPercent(status.return_percentage)})</span>
					</p>
				{:else}
					<p class="text-surface-500 text-xs">—</p>
				{/if}
			</div>
			<div>
				<p class="text-surface-400 text-xs">Días activa</p>
				{#if status}
					<p class="text-surface-100">{status.days_held} días</p>
				{:else}
					<p class="text-surface-500 text-xs">—</p>
				{/if}
			</div>
		</div>

		<!-- Fechas -->
		<div class="text-xs text-surface-400 space-y-1">
			<p>Inicio: <span class="text-surface-300">{formatDate(investment.start_date)}</span></p>
			{#if investment.maturity_date}
				<p>
					Vencimiento: <span class="{maturingSoon ? 'text-warning-400' : maturityPast ? 'text-error-400' : 'text-surface-300'} font-medium">
						{formatDate(investment.maturity_date)}
						{#if daysToMaturity !== null && daysToMaturity >= 0}
							<span class="text-surface-400 font-normal">({daysToMaturity}d)</span>
						{/if}
					</span>
				</p>
				{#if investment.auto_renew}
					<p class="text-tertiary-400">♻ Renovación automática ({investment.renewal_period_months} meses)</p>
				{/if}
			{/if}
		</div>

		<!-- Acciones -->
		{#if confirmDelete}
			<div class="flex items-center gap-2 text-sm">
				<span class="text-warning-400 text-xs">¿Eliminar inversión?</span>
				<button class="btn btn-sm variant-filled-error" on:click={handleDelete}>Sí</button>
				<button class="btn btn-sm variant-ghost-surface" on:click={() => (confirmDelete = false)}>No</button>
			</div>
		{:else}
			<div class="flex gap-2 flex-wrap">
				<button
					class="btn btn-sm variant-soft flex-1"
					on:click={() => dispatch('edit', { investment })}
				>
					Editar
				</button>
				{#if investment.maturity_date && investment.renewal_period_months}
					<button
						class="btn btn-sm variant-soft-tertiary"
						on:click={() => dispatch('renew', { id: investment.id })}
						title="Renovar por {investment.renewal_period_months} meses más"
					>
						Renovar
					</button>
				{/if}
				<button class="btn btn-sm variant-ghost-error" on:click={handleDelete}>
					Eliminar
				</button>
			</div>
		{/if}
	{/if}
</div>
