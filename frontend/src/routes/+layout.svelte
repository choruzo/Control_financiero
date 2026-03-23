<script lang="ts">
	import '../app.postcss';
	import { Modal, Toast, initializeStores, setInitialClassState } from '@skeletonlabs/skeleton';

	// Inicializar los stores internos de Skeleton (Modal, Toast, Drawer)
	initializeStores();

	// Aplicar la preferencia de tema guardada (oscuro/claro) antes del primer render
	setInitialClassState();
</script>

<!-- Portales de Skeleton: deben estar en el layout raíz -->
<Modal />
<Toast />

<slot />
