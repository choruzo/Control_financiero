<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { CategoryResponse } from '$lib/types';

	export let category: CategoryResponse;

	const dispatch = createEventDispatcher<{
		edit: { category: CategoryResponse };
		delete: { id: string };
	}>();

	let confirmDelete = false;

	function handleDelete() {
		if (confirmDelete) {
			dispatch('delete', { id: category.id });
			confirmDelete = false;
		} else {
			confirmDelete = true;
		}
	}
</script>

<div class="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-surface-700 transition-colors">
	<div class="flex items-center gap-3">
		{#if category.icon}
			<span class="text-lg">{category.icon}</span>
		{/if}
		{#if category.color}
			<div
				class="w-3 h-3 rounded-full flex-shrink-0"
				style="background-color: {category.color}"
			></div>
		{/if}
		<span class="text-sm font-medium">{category.name}</span>
		{#if category.is_system}
			<span class="badge variant-ghost-surface text-xs">Sistema</span>
		{/if}
	</div>

	{#if !category.is_system}
		<div class="flex gap-1">
			<button
				class="btn btn-sm variant-ghost-surface"
				on:click={() => dispatch('edit', { category })}
			>
				Editar
			</button>
			<button
				class="btn btn-sm"
				class:variant-ghost-error={!confirmDelete}
				class:variant-filled-error={confirmDelete}
				on:click={handleDelete}
			>
				{confirmDelete ? '¿Confirmar?' : 'Eliminar'}
			</button>
		</div>
	{/if}
</div>
