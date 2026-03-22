<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { TabGroup, Tab } from '@skeletonlabs/skeleton';
	import { authStore } from '$lib/stores/auth';
	import { login, register } from '$lib/api/auth';
	import { setTokens } from '$lib/api/client';

	let tabSet = 0; // 0 = login, 1 = registro
	let email = '';
	let password = '';
	let confirmPassword = '';
	let errorMsg = '';
	let isLoading = false;

	// URL a la que redirigir después del login (preservada en query param)
	$: redirectTo = $page.url.searchParams.get('redirect') ?? '/dashboard';

	async function handleLogin() {
		errorMsg = '';
		isLoading = true;
		try {
			const tokens = await login(email, password);
			setTokens(tokens.access_token, tokens.refresh_token);
			await authStore.loadUser();
			goto(redirectTo);
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : 'Error al iniciar sesión';
		} finally {
			isLoading = false;
		}
	}

	async function handleRegister() {
		errorMsg = '';
		if (password !== confirmPassword) {
			errorMsg = 'Las contraseñas no coinciden';
			return;
		}
		if (password.length < 8) {
			errorMsg = 'La contraseña debe tener al menos 8 caracteres';
			return;
		}
		isLoading = true;
		try {
			const tokens = await register({ email, password });
			setTokens(tokens.access_token, tokens.refresh_token);
			await authStore.loadUser();
			goto('/dashboard');
		} catch (e) {
			errorMsg = e instanceof Error ? e.message : 'Error al registrarse';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="min-h-screen flex items-center justify-center bg-surface-900 p-4">
	<div class="card p-8 w-full max-w-md space-y-6 bg-surface-800">
		<div class="text-center">
			<h1 class="h1 text-2xl font-bold text-primary-400">FinControl</h1>
			<p class="text-surface-400 mt-1">Control financiero personal</p>
		</div>

		<TabGroup>
			<Tab bind:group={tabSet} name="tab-login" value={0}>Iniciar sesión</Tab>
			<Tab bind:group={tabSet} name="tab-register" value={1}>Registrarse</Tab>

			<svelte:fragment slot="panel">
				{#if tabSet === 0}
					<!-- Panel Login -->
					<form on:submit|preventDefault={handleLogin} class="space-y-4 mt-4">
						<label class="label">
							<span>Email</span>
							<input
								class="input"
								type="email"
								bind:value={email}
								placeholder="usuario@ejemplo.com"
								required
								autocomplete="email"
							/>
						</label>
						<label class="label">
							<span>Contraseña</span>
							<input
								class="input"
								type="password"
								bind:value={password}
								placeholder="••••••••"
								required
								autocomplete="current-password"
							/>
						</label>
						{#if errorMsg}
							<p class="text-error-400 text-sm" role="alert">{errorMsg}</p>
						{/if}
						<button type="submit" class="btn variant-filled-primary w-full" disabled={isLoading}>
							{isLoading ? 'Cargando...' : 'Entrar'}
						</button>
					</form>
				{:else}
					<!-- Panel Registro -->
					<form on:submit|preventDefault={handleRegister} class="space-y-4 mt-4">
						<label class="label">
							<span>Email</span>
							<input
								class="input"
								type="email"
								bind:value={email}
								placeholder="usuario@ejemplo.com"
								required
								autocomplete="email"
							/>
						</label>
						<label class="label">
							<span>Contraseña</span>
							<input
								class="input"
								type="password"
								bind:value={password}
								placeholder="Mínimo 8 caracteres"
								required
								autocomplete="new-password"
							/>
						</label>
						<label class="label">
							<span>Confirmar contraseña</span>
							<input
								class="input"
								type="password"
								bind:value={confirmPassword}
								placeholder="Repite la contraseña"
								required
								autocomplete="new-password"
							/>
						</label>
						{#if errorMsg}
							<p class="text-error-400 text-sm" role="alert">{errorMsg}</p>
						{/if}
						<button type="submit" class="btn variant-filled-primary w-full" disabled={isLoading}>
							{isLoading ? 'Creando cuenta...' : 'Crear cuenta'}
						</button>
					</form>
				{/if}
			</svelte:fragment>
		</TabGroup>
	</div>
</div>
