<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { AppShell, AppBar, LightSwitch } from '@skeletonlabs/skeleton';
	import { onMount } from 'svelte';
	import { authStore, currentUser } from '$lib/stores/auth';
	import { sidebarOpen, toggleSidebar } from '$lib/stores/ui';

	// Restaurar sesión tras recarga de página
	onMount(async () => {
		if (!$authStore.isAuthenticated) {
			const ok = await authStore.loadUser();
			if (!ok) goto('/login');
		}
	});

	function handleLogout() {
		authStore.logout();
		goto('/login');
	}

	// Elementos de navegación del sidebar
	const navItems = [
		{ href: '/dashboard', icon: '📊', label: 'Dashboard' },
		{ href: '/transactions', icon: '💳', label: 'Transacciones' },
		{ href: '/budgets', icon: '📋', label: 'Presupuestos' },
		{ href: '/investments', icon: '📈', label: 'Inversiones' },
		{ href: '/mortgage', icon: '🏠', label: 'Hipoteca' },
		{ href: '/predictions', icon: '🔮', label: 'Predicciones' },
		{ href: '/settings', icon: '⚙️', label: 'Configuración' }
	];

	$: currentPath = $page.url.pathname;
</script>

<AppShell>
	<svelte:fragment slot="header">
		<AppBar>
			<svelte:fragment slot="lead">
				<!-- Botón hamburguesa para mobile -->
				<button
					class="btn btn-sm variant-ghost-surface lg:hidden mr-2"
					on:click={toggleSidebar}
					aria-label="Abrir menú lateral"
				>
					<span class="text-lg">☰</span>
				</button>
				<span class="text-xl font-bold text-primary-400">FinControl</span>
			</svelte:fragment>

			<svelte:fragment slot="trail">
				<span class="text-sm text-surface-400 hidden sm:inline">
					{$currentUser?.email ?? ''}
				</span>
				<LightSwitch />
				<button class="btn btn-sm variant-ghost-error" on:click={handleLogout}>
					Salir
				</button>
			</svelte:fragment>
		</AppBar>
	</svelte:fragment>

	<svelte:fragment slot="sidebarLeft">
		<!-- Desktop: siempre visible | Mobile: controlado por sidebarOpen -->
		<nav
			class="h-full bg-surface-800 w-60 flex-col p-4 space-y-1 hidden lg:flex"
			class:flex={$sidebarOpen}
		>
			{#each navItems as item}
				<a
					href={item.href}
					class="flex items-center gap-3 px-3 py-2 rounded-lg text-surface-200 hover:bg-surface-700 transition-colors"
					class:bg-primary-500={currentPath.startsWith(item.href)}
					class:text-white={currentPath.startsWith(item.href)}
					on:click={() => sidebarOpen.set(false)}
				>
					<span class="text-lg">{item.icon}</span>
					<span>{item.label}</span>
				</a>
			{/each}
		</nav>
	</svelte:fragment>

	<!-- Contenido principal -->
	<div class="p-4 lg:p-6">
		<slot />
	</div>
</AppShell>
