<script lang="ts">
	import type { MLModelStatus } from '$lib/types';

	export let status: MLModelStatus | null = null;
	export let loading: boolean = false;
	export let title: string = 'Modelo ML';
</script>

<div class="card p-4 bg-surface-700 space-y-3">
	<div class="flex items-center justify-between">
		<h3 class="font-semibold text-surface-100">{title}</h3>
		{#if loading}
			<span class="badge variant-ghost-surface animate-pulse">Cargando...</span>
		{:else if status === null}
			<span class="badge variant-ghost-surface text-surface-400">Sin datos</span>
		{:else if !status.ml_available}
			<span class="badge variant-filled-error">Servicio no disponible</span>
		{:else if status.loaded}
			<span class="badge variant-filled-success">Activo</span>
		{:else}
			<span class="badge variant-filled-warning">Sin modelo</span>
		{/if}
	</div>

	{#if loading}
		<div class="space-y-2">
			{#each [1, 2, 3, 4] as _}
				<div class="animate-pulse h-5 bg-surface-600 rounded w-3/4"></div>
			{/each}
		</div>
	{:else if status === null || !status.ml_available}
		<p class="text-sm text-surface-400">
			{status === null ? 'No se pudo obtener el estado del modelo.' : 'El servicio ML no está disponible. Comprueba que el contenedor ml-service esté activo.'}
		</p>
	{:else}
		<dl class="space-y-2 text-sm">
			<div class="flex justify-between">
				<dt class="text-surface-400">Versión</dt>
				<dd class="font-medium">{status.version ?? '—'}</dd>
			</div>
			<div class="flex justify-between">
				<dt class="text-surface-400">Precisión</dt>
				<dd class="font-medium">
					{status.accuracy !== null ? `${(status.accuracy * 100).toFixed(1)}%` : '—'}
				</dd>
			</div>
			<div class="flex justify-between">
				<dt class="text-surface-400">Último entrenamiento</dt>
				<dd class="font-medium">
					{#if status.last_trained}
						{new Date(status.last_trained).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })}
					{:else}
						—
					{/if}
				</dd>
			</div>
			<div class="flex justify-between">
				<dt class="text-surface-400">Feedback pendiente</dt>
				<dd class="font-medium">
					<span class:text-yellow-400={status.feedback_count > 5}>
						{status.feedback_count} muestras
					</span>
				</dd>
			</div>
			<div class="flex justify-between">
				<dt class="text-surface-400">Estado</dt>
				<dd>
					{#if status.retrain_in_progress}
						<span class="badge variant-filled-warning text-xs animate-pulse">Reentrenando...</span>
					{:else}
						<span class="text-surface-300">Inactivo</span>
					{/if}
				</dd>
			</div>
		</dl>
	{/if}
</div>
