<script lang="ts">
	import '../app.postcss';
	import { Modal, Toast, initializeStores, computeLightSwitch } from '@skeletonlabs/skeleton';
	import { onMount } from 'svelte';

	// Inicializar los stores internos de Skeleton (Modal, Toast, Drawer)
	initializeStores();

	// Aplicar la preferencia de tema guardada (oscuro/claro) antes del primer render
	onMount(() => computeLightSwitch());
</script>

<!-- Portales de Skeleton: deben estar en el layout raíz -->
<Modal />
<Toast />

<slot />
