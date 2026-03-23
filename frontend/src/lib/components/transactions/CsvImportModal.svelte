<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { formatCurrency } from '$lib/utils/format';
	import type { AccountResponse, ImportResult, ImportRowResult } from '$lib/types';

	export let show = false;
	export let accounts: AccountResponse[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
		imported: { result: ImportResult };
	}>();

	type Step = 'select' | 'preview' | 'done';
	let step: Step = 'select';

	let selectedAccountId = '';
	let selectedFile: File | null = null;
	let previewResult: ImportResult | null = null;
	let finalResult: ImportResult | null = null;
	let isLoading = false;
	let error = '';

	// Inicializar cuando se abre
	$: if (show) {
		step = 'select';
		selectedAccountId = accounts[0]?.id ?? '';
		selectedFile = null;
		previewResult = null;
		finalResult = null;
		isLoading = false;
		error = '';
	}

	function handleFileChange(e: Event) {
		const input = e.target as HTMLInputElement;
		selectedFile = input.files?.[0] ?? null;
		error = '';
	}

	async function runPreview() {
		if (!selectedFile || !selectedAccountId) {
			error = 'Selecciona un archivo CSV y una cuenta.';
			return;
		}
		isLoading = true;
		error = '';
		try {
			const { importCsv } = await import('$lib/api/transactions');
			previewResult = await importCsv(selectedFile, selectedAccountId, true);
			step = 'preview';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Error al procesar el archivo CSV.';
		} finally {
			isLoading = false;
		}
	}

	async function confirmImport() {
		if (!selectedFile || !selectedAccountId) return;
		isLoading = true;
		error = '';
		try {
			const { importCsv } = await import('$lib/api/transactions');
			finalResult = await importCsv(selectedFile, selectedAccountId, false);
			step = 'done';
			dispatch('imported', { result: finalResult });
		} catch (e) {
			error = e instanceof Error ? e.message : 'Error al importar el archivo CSV.';
		} finally {
			isLoading = false;
		}
	}

	function handleClose() {
		if (!isLoading) dispatch('close');
	}

	function statusBadge(row: ImportRowResult): string {
		if (row.status === 'imported') return 'variant-filled-success';
		if (row.status === 'skipped_duplicate') return 'variant-filled-warning';
		return 'variant-filled-error';
	}

	function statusLabel(row: ImportRowResult): string {
		if (row.status === 'imported') return '✓ Importada';
		if (row.status === 'skipped_duplicate') return '⚠ Duplicada';
		return '✕ Error';
	}
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4"
		on:click|self={handleClose}
	>
		<div class="card w-full max-w-2xl bg-surface-800 shadow-xl z-50 overflow-hidden max-h-[90vh] flex flex-col">
			<!-- Header -->
			<header class="card-header flex items-center justify-between flex-shrink-0">
				<div>
					<h3 class="h4">Importar transacciones CSV</h3>
					<!-- Stepper -->
					<div class="flex items-center gap-2 mt-1 text-sm">
						<span class={step === 'select' ? 'text-primary-400 font-medium' : 'text-surface-400'}>
							1. Selección
						</span>
						<span class="text-surface-600">›</span>
						<span class={step === 'preview' ? 'text-primary-400 font-medium' : 'text-surface-400'}>
							2. Vista previa
						</span>
						<span class="text-surface-600">›</span>
						<span class={step === 'done' ? 'text-success-400 font-medium' : 'text-surface-400'}>
							3. Resultado
						</span>
					</div>
				</div>
				<button
					type="button"
					class="btn btn-icon btn-sm variant-soft"
					on:click={handleClose}
					disabled={isLoading}
				>✕</button>
			</header>

			<!-- Contenido scrollable -->
			<div class="p-4 overflow-y-auto flex-1">

				<!-- PASO 1: Selección de archivo y cuenta -->
				{#if step === 'select'}
					<div class="space-y-4">
						<p class="text-sm text-surface-400">
							Selecciona un archivo CSV exportado desde OpenBank y la cuenta destino.
							Se mostrará una vista previa antes de importar.
						</p>

						<label class="label">
							<span>Cuenta destino <span class="text-error-400">*</span></span>
							<select class="select" bind:value={selectedAccountId}>
								<option value="" disabled>Selecciona una cuenta</option>
								{#each accounts as acc}
									<option value={acc.id}>{acc.name} — {acc.bank}</option>
								{/each}
							</select>
						</label>

						<label class="label">
							<span>Archivo CSV <span class="text-error-400">*</span></span>
							<input
								type="file"
								accept=".csv,text/csv"
								class="input"
								on:change={handleFileChange}
							/>
							{#if selectedFile}
								<span class="text-xs text-surface-400 mt-1">{selectedFile.name}</span>
							{/if}
						</label>

						{#if error}
							<div class="alert variant-filled-error text-sm p-3">{error}</div>
						{/if}

						<div class="flex justify-end gap-3">
							<button type="button" class="btn variant-soft" on:click={handleClose}>
								Cancelar
							</button>
							<button
								type="button"
								class="btn variant-filled-primary"
								on:click={runPreview}
								disabled={isLoading || !selectedFile || !selectedAccountId}
							>
								{isLoading ? 'Procesando...' : 'Ver vista previa →'}
							</button>
						</div>
					</div>

				<!-- PASO 2: Vista previa (dry_run=true) -->
				{:else if step === 'preview' && previewResult}
					<div class="space-y-4">
						<!-- Resumen -->
						<div class="grid grid-cols-3 gap-3">
							<div class="card p-3 variant-soft-success text-center">
								<div class="text-2xl font-bold text-success-400">{previewResult.imported}</div>
								<div class="text-xs text-surface-400">A importar</div>
							</div>
							<div class="card p-3 variant-soft-warning text-center">
								<div class="text-2xl font-bold text-warning-400">{previewResult.skipped_duplicates}</div>
								<div class="text-xs text-surface-400">Duplicadas</div>
							</div>
							<div class="card p-3 variant-soft-error text-center">
								<div class="text-2xl font-bold text-error-400">{previewResult.errors}</div>
								<div class="text-xs text-surface-400">Errores</div>
							</div>
						</div>

						<!-- Tabla de filas -->
						<div class="overflow-x-auto max-h-80 overflow-y-auto rounded border border-surface-700">
							<table class="table table-compact w-full text-sm">
								<thead class="sticky top-0 bg-surface-800">
									<tr>
										<th class="px-3 py-2">#</th>
										<th class="px-3 py-2">Descripción</th>
										<th class="px-3 py-2 text-right">Importe</th>
										<th class="px-3 py-2">Fecha</th>
										<th class="px-3 py-2">Estado</th>
									</tr>
								</thead>
								<tbody>
									{#each previewResult.rows as row}
										<tr class="border-t border-surface-700/50">
											<td class="px-3 py-2 text-surface-400">{row.row}</td>
											<td class="px-3 py-2 max-w-xs truncate">
												{row.description ?? row.error_detail ?? '—'}
											</td>
											<td class="px-3 py-2 text-right">
												{#if row.amount !== undefined}
													{formatCurrency(row.amount)}
												{:else}
													—
												{/if}
											</td>
											<td class="px-3 py-2 text-surface-400">{row.date ?? '—'}</td>
											<td class="px-3 py-2">
												<span class="badge {statusBadge(row)} text-xs">{statusLabel(row)}</span>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>

						{#if error}
							<div class="alert variant-filled-error text-sm p-3">{error}</div>
						{/if}

						<div class="flex justify-between gap-3">
							<button
								type="button"
								class="btn variant-soft"
								on:click={() => (step = 'select')}
								disabled={isLoading}
							>← Volver</button>
							<button
								type="button"
								class="btn variant-filled-success"
								on:click={confirmImport}
								disabled={isLoading || previewResult.imported === 0}
							>
								{isLoading
									? 'Importando...'
									: `Importar ${previewResult.imported} transacciones`}
							</button>
						</div>
					</div>

				<!-- PASO 3: Resultado final -->
				{:else if step === 'done' && finalResult}
					<div class="space-y-4 text-center py-4">
						<div class="text-5xl">✅</div>
						<h4 class="h4">Importación completada</h4>
						<div class="grid grid-cols-2 gap-3 text-left max-w-sm mx-auto">
							<div class="card p-3 variant-soft-success">
								<div class="text-2xl font-bold text-success-400">{finalResult.imported}</div>
								<div class="text-sm text-surface-400">Transacciones importadas</div>
							</div>
							<div class="card p-3 variant-soft-warning">
								<div class="text-2xl font-bold text-warning-400">{finalResult.skipped_duplicates}</div>
								<div class="text-sm text-surface-400">Duplicadas omitidas</div>
							</div>
						</div>
						<div class="flex justify-center">
							<button type="button" class="btn variant-filled-primary" on:click={handleClose}>
								Cerrar
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
