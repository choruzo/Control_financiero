<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { BudgetResponse, BudgetCreate, BudgetUpdate, CategoryResponse } from '$lib/types';

	export let show = false;
	export let budget: BudgetResponse | null = null;
	export let categories: CategoryResponse[] = [];
	/** IDs de categorías que ya tienen presupuesto en el período (para filtrar en creación) */
	export let usedCategoryIds: string[] = [];
	export let year: number;
	export let month: number;

	const dispatch = createEventDispatcher<{
		close: void;
		saved: { budget: BudgetResponse };
	}>();

	$: isEditing = budget !== null;
	$: title = isEditing ? 'Editar presupuesto' : 'Nuevo presupuesto';

	// Categorías disponibles: excluye las que ya tienen presupuesto (solo en creación)
	$: availableCategories = isEditing
		? categories
		: categories.filter((c) => !usedCategoryIds.includes(c.id));

	let categoryId = '';
	let name = '';
	let limitAmount = '';
	let alertThreshold = '80';
	let isSaving = false;
	let error = '';

	// Resetear formulario cuando show cambia
	$: if (show) {
		if (budget) {
			categoryId = budget.category_id;
			name = budget.name ?? '';
			limitAmount = String(budget.limit_amount);
			alertThreshold = String(budget.alert_threshold);
		} else {
			categoryId = '';
			name = '';
			limitAmount = '';
			alertThreshold = '80';
		}
		error = '';
	}

	async function handleSubmit() {
		if (!limitAmount || parseFloat(limitAmount) <= 0) {
			error = 'El límite debe ser mayor que cero';
			return;
		}
		const threshold = parseFloat(alertThreshold);
		if (isNaN(threshold) || threshold < 0 || threshold > 100) {
			error = 'El umbral debe estar entre 0 y 100';
			return;
		}
		if (!isEditing && !categoryId) {
			error = 'Selecciona una categoría';
			return;
		}

		isSaving = true;
		error = '';

		try {
			const { createBudget, updateBudget } = await import('$lib/api/budgets');
			let saved: BudgetResponse;

			if (isEditing && budget) {
				const updateData: BudgetUpdate = {
					limit_amount: parseFloat(limitAmount),
					alert_threshold: threshold
				};
				if (name.trim()) updateData.name = name.trim();
				else updateData.name = undefined;
				saved = await updateBudget(budget.id, updateData);
			} else {
				const createData: BudgetCreate = {
					category_id: categoryId,
					period_year: year,
					period_month: month,
					limit_amount: parseFloat(limitAmount),
					alert_threshold: threshold
				};
				if (name.trim()) createData.name = name.trim();
				saved = await createBudget(createData);
			}

			dispatch('saved', { budget: saved });
			dispatch('close');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Error al guardar el presupuesto';
		} finally {
			isSaving = false;
		}
	}

	const MONTH_NAMES = [
		'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
		'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
	];
</script>

{#if show}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/60 z-40 flex items-center justify-center p-4"
		role="dialog"
		aria-modal="true"
		aria-label={title}
	>
		<div class="card w-full max-w-md z-50" on:click|stopPropagation>
			<header class="card-header flex items-center justify-between">
				<h3 class="h3">{title}</h3>
				<button
					class="btn btn-sm variant-ghost-surface"
					on:click={() => dispatch('close')}
					disabled={isSaving}
					aria-label="Cerrar"
				>
					✕
				</button>
			</header>

			<form on:submit|preventDefault={handleSubmit} class="p-4 space-y-4">
				<!-- Período (informativo) -->
				<p class="text-sm text-surface-400">
					Período: <span class="text-surface-200">{MONTH_NAMES[month - 1]} {year}</span>
				</p>

				<!-- Categoría -->
				<label class="label">
					<span>Categoría <span class="text-error-400">*</span></span>
					{#if isEditing}
						<!-- En edición, mostrar la categoría pero no permitir cambio -->
						<input
							type="text"
							class="input"
							value={categories.find((c) => c.id === budget?.category_id)?.name ?? budget?.category_id}
							disabled
						/>
					{:else}
						<select class="select" bind:value={categoryId} required>
							<option value="">-- Seleccionar categoría --</option>
							{#each availableCategories as cat}
								<option value={cat.id}>{cat.name}</option>
							{/each}
						</select>
						{#if availableCategories.length === 0}
							<p class="text-xs text-warning-400 mt-1">
								Todas las categorías ya tienen presupuesto este mes.
							</p>
						{/if}
					{/if}
				</label>

				<!-- Nombre (opcional) -->
				<label class="label">
					<span>Nombre personalizado <span class="text-surface-400 text-xs">(opcional)</span></span>
					<input
						type="text"
						class="input"
						placeholder="Ej: Alimentación mensual"
						bind:value={name}
						maxlength="100"
					/>
				</label>

				<!-- Límite -->
				<label class="label">
					<span>Límite (€) <span class="text-error-400">*</span></span>
					<input
						type="number"
						class="input"
						placeholder="0.00"
						bind:value={limitAmount}
						min="0.01"
						step="0.01"
						required
					/>
				</label>

				<!-- Umbral de alerta -->
				<label class="label">
					<span>Umbral de alerta (%)</span>
					<div class="flex items-center gap-2">
						<input
							type="range"
							class="flex-1"
							bind:value={alertThreshold}
							min="0"
							max="100"
							step="5"
						/>
						<span class="text-sm w-10 text-right text-surface-200">{alertThreshold}%</span>
					</div>
					<p class="text-xs text-surface-400 mt-1">
						Se generará una alerta cuando el gasto supere este porcentaje del límite.
					</p>
				</label>

				{#if error}
					<div class="alert variant-filled-error text-sm">{error}</div>
				{/if}

				<div class="flex justify-end gap-3 pt-2">
					<button
						type="button"
						class="btn variant-ghost-surface"
						on:click={() => dispatch('close')}
						disabled={isSaving}
					>
						Cancelar
					</button>
					<button type="submit" class="btn variant-filled-primary" disabled={isSaving}>
						{isSaving ? 'Guardando...' : isEditing ? 'Guardar cambios' : 'Crear presupuesto'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}
