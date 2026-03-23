<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { CategoryResponse, CategoryCreate, CategoryUpdate } from '$lib/types';

	export let show = false;
	export let editingCategory: CategoryResponse | null = null;
	export let parentCategories: CategoryResponse[] = [];

	const dispatch = createEventDispatcher<{
		save: { data: CategoryCreate | CategoryUpdate; id?: string };
		close: void;
	}>();

	let name = '';
	let color = '#6366f1';
	let icon = '';
	let parentId = '';
	let saving = false;
	let error = '';

	$: if (show) {
		if (editingCategory) {
			name = editingCategory.name;
			color = editingCategory.color ?? '#6366f1';
			icon = editingCategory.icon ?? '';
			parentId = editingCategory.parent_id ?? '';
		} else {
			name = '';
			color = '#6366f1';
			icon = '';
			parentId = '';
		}
		error = '';
	}

	async function handleSubmit() {
		if (!name.trim()) {
			error = 'El nombre es obligatorio';
			return;
		}
		saving = true;
		error = '';
		const data: CategoryCreate = {
			name: name.trim(),
			color: color || undefined,
			icon: icon.trim() || undefined,
			parent_id: parentId || undefined
		};
		dispatch('save', { data, id: editingCategory?.id });
		saving = false;
	}
</script>

{#if show}
	<div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
		<div class="card bg-surface-800 shadow-xl p-6 w-full max-w-md space-y-4">
			<h3 class="font-semibold text-lg">
				{editingCategory ? 'Editar categoría' : 'Nueva categoría'}
			</h3>

			{#if error}
				<aside class="alert variant-ghost-error text-sm">{error}</aside>
			{/if}

			<label class="label">
				<span>Nombre <span class="text-error-400">*</span></span>
				<input class="input" type="text" bind:value={name} placeholder="Ej: Alimentación" maxlength="100" />
			</label>

			<div class="grid grid-cols-2 gap-4">
				<label class="label">
					<span>Icono (emoji)</span>
					<input class="input" type="text" bind:value={icon} placeholder="🍕" maxlength="4" />
				</label>
				<label class="label">
					<span>Color</span>
					<div class="flex items-center gap-2">
						<input type="color" class="h-10 w-14 rounded cursor-pointer" bind:value={color} />
						<input class="input text-xs font-mono" type="text" bind:value={color} maxlength="7" />
					</div>
				</label>
			</div>

			{#if parentCategories.length > 0 && !editingCategory}
				<label class="label">
					<span>Categoría padre (opcional)</span>
					<select class="select" bind:value={parentId}>
						<option value="">Sin categoría padre</option>
						{#each parentCategories as cat}
							<option value={cat.id}>{cat.icon ? cat.icon + ' ' : ''}{cat.name}</option>
						{/each}
					</select>
				</label>
			{/if}

			<div class="flex justify-end gap-2 pt-2">
				<button class="btn variant-ghost" on:click={() => dispatch('close')}>
					Cancelar
				</button>
				<button
					class="btn variant-filled-primary"
					on:click={handleSubmit}
					disabled={saving || !name.trim()}
				>
					{saving ? 'Guardando…' : 'Guardar'}
				</button>
			</div>
		</div>
	</div>
{/if}
