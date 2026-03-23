<script lang="ts">
	import { onMount } from 'svelte';
	import { createEventDispatcher } from 'svelte';
	import { currentUser } from '$lib/stores/auth';
	import { getAccounts, createAccount, updateAccount, deleteAccount } from '$lib/api/accounts';
	import { formatCurrency } from '$lib/utils/format';
	import type { AccountResponse, AccountCreate, AccountType } from '$lib/types';

	const dispatch = createEventDispatcher();

	let accounts: AccountResponse[] = [];
	let loadingAccounts = true;
	let errorAccounts = '';

	// Formulario de cuenta
	let showAccountForm = false;
	let editingAccount: AccountResponse | null = null;
	let confirmDeleteId: string | null = null;
	let savingAccount = false;

	let formName = '';
	let formBank = '';
	let formType: AccountType = 'checking';
	let formBalance = 0;
	let formCurrency = 'EUR';

	const accountTypeLabels: Record<AccountType, string> = {
		checking: 'Cuenta corriente',
		savings: 'Cuenta de ahorro',
		investment: 'Inversión',
		credit: 'Crédito'
	};

	onMount(async () => {
		await loadAccounts();
	});

	async function loadAccounts() {
		loadingAccounts = true;
		errorAccounts = '';
		try {
			accounts = await getAccounts();
		} catch {
			errorAccounts = 'No se pudieron cargar las cuentas';
		} finally {
			loadingAccounts = false;
		}
	}

	function openNewAccount() {
		editingAccount = null;
		formName = '';
		formBank = '';
		formType = 'checking';
		formBalance = 0;
		formCurrency = 'EUR';
		showAccountForm = true;
	}

	function openEditAccount(account: AccountResponse) {
		editingAccount = account;
		formName = account.name;
		formBank = account.bank;
		formType = account.account_type;
		formBalance = account.balance;
		formCurrency = account.currency;
		showAccountForm = true;
	}

	async function saveAccount() {
		if (!formName.trim() || !formBank.trim()) return;
		savingAccount = true;
		try {
			if (editingAccount) {
				const updated = await updateAccount(editingAccount.id, {
					name: formName,
					bank: formBank,
					account_type: formType,
					balance: formBalance,
					currency: formCurrency
				});
				accounts = accounts.map((a) => (a.id === editingAccount!.id ? updated : a));
			} else {
				const created = await createAccount({
					name: formName,
					bank: formBank,
					account_type: formType,
					balance: formBalance,
					currency: formCurrency
				});
				accounts = [...accounts, created];
			}
			showAccountForm = false;
		} catch {
			// error silencioso — el formulario sigue abierto
		} finally {
			savingAccount = false;
		}
	}

	async function handleDeleteAccount(id: string) {
		if (confirmDeleteId !== id) {
			confirmDeleteId = id;
			return;
		}
		confirmDeleteId = null;
		accounts = accounts.filter((a) => a.id !== id);
		try {
			await deleteAccount(id);
		} catch {
			await loadAccounts();
		}
	}
</script>

<div class="space-y-6">
	<!-- Info del usuario -->
	<div class="card p-4 space-y-3">
		<h3 class="font-semibold text-surface-200">Información de cuenta</h3>
		{#if $currentUser}
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
				<div>
					<p class="text-surface-400">Email</p>
					<p class="font-mono">{$currentUser.email}</p>
				</div>
				<div>
					<p class="text-surface-400">Miembro desde</p>
					<p>{new Date($currentUser.created_at).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
				</div>
				<div>
					<p class="text-surface-400">Estado</p>
					<span class="badge variant-filled-success text-xs">Activo</span>
				</div>
			</div>
		{:else}
			<div class="animate-pulse space-y-2">
				<div class="h-4 bg-surface-600 rounded w-48"></div>
				<div class="h-4 bg-surface-600 rounded w-32"></div>
			</div>
		{/if}
	</div>

	<!-- Cuentas bancarias -->
	<div class="space-y-3">
		<div class="flex items-center justify-between">
			<h3 class="font-semibold text-surface-200">Cuentas bancarias</h3>
			<button class="btn btn-sm variant-filled-primary" on:click={openNewAccount}>
				+ Nueva cuenta
			</button>
		</div>

		{#if loadingAccounts}
			<div class="space-y-2">
				{#each [1, 2] as _}
					<div class="card p-4 animate-pulse">
						<div class="h-4 bg-surface-600 rounded w-48 mb-2"></div>
						<div class="h-3 bg-surface-600 rounded w-32"></div>
					</div>
				{/each}
			</div>
		{:else if errorAccounts}
			<aside class="alert variant-ghost-error">
				<p>{errorAccounts}</p>
				<button class="btn btn-sm" on:click={loadAccounts}>Reintentar</button>
			</aside>
		{:else if accounts.length === 0}
			<div class="card p-6 text-center text-surface-400">
				<p>No tienes cuentas registradas</p>
				<button class="btn btn-sm variant-ghost-primary mt-2" on:click={openNewAccount}>
					Crear primera cuenta
				</button>
			</div>
		{:else}
			<div class="space-y-2">
				{#each accounts as account (account.id)}
					<div class="card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
						<div>
							<div class="flex items-center gap-2">
								<span class="font-medium">{account.name}</span>
								<span class="badge variant-ghost text-xs">{accountTypeLabels[account.account_type]}</span>
								{#if !account.is_active}
									<span class="badge variant-ghost-surface text-xs">Inactiva</span>
								{/if}
							</div>
							<p class="text-sm text-surface-400">{account.bank}</p>
						</div>
						<div class="flex items-center gap-3">
							<span class="font-mono font-semibold">{formatCurrency(account.balance)}</span>
							<button class="btn btn-sm variant-ghost-surface" on:click={() => openEditAccount(account)}>
								Editar
							</button>
							<button
								class="btn btn-sm"
								class:variant-ghost-error={confirmDeleteId !== account.id}
								class:variant-filled-error={confirmDeleteId === account.id}
								on:click={() => handleDeleteAccount(account.id)}
							>
								{confirmDeleteId === account.id ? '¿Confirmar?' : 'Eliminar'}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Modal formulario cuenta -->
	{#if showAccountForm}
		<div class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
			<div class="card bg-surface-800 shadow-xl p-6 w-full max-w-md space-y-4">
				<h3 class="font-semibold text-lg">
					{editingAccount ? 'Editar cuenta' : 'Nueva cuenta'}
				</h3>

				<label class="label">
					<span>Nombre</span>
					<input class="input" type="text" bind:value={formName} placeholder="Mi cuenta corriente" />
				</label>

				<label class="label">
					<span>Banco</span>
					<input class="input" type="text" bind:value={formBank} placeholder="OpenBank" />
				</label>

				<label class="label">
					<span>Tipo</span>
					<select class="select" bind:value={formType}>
						{#each Object.entries(accountTypeLabels) as [value, label]}
							<option {value}>{label}</option>
						{/each}
					</select>
				</label>

				<label class="label">
					<span>Saldo inicial (€)</span>
					<input class="input" type="number" step="0.01" bind:value={formBalance} />
				</label>

				<div class="flex justify-end gap-2 pt-2">
					<button class="btn variant-ghost" on:click={() => (showAccountForm = false)}>
						Cancelar
					</button>
					<button
						class="btn variant-filled-primary"
						on:click={saveAccount}
						disabled={savingAccount || !formName.trim() || !formBank.trim()}
					>
						{savingAccount ? 'Guardando…' : 'Guardar'}
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
