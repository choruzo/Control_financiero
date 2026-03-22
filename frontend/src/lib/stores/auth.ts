import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import type { User, AuthState } from '$lib/types';
import { setTokens, clearTokens } from '$lib/api/client';
import { getMe } from '$lib/api/auth';

function createAuthStore() {
	const initialState: AuthState = {
		user: null,
		accessToken: browser ? localStorage.getItem('fc_access_token') : null,
		refreshToken: browser ? localStorage.getItem('fc_refresh_token') : null,
		isAuthenticated: false,
		isLoading: false
	};

	const { subscribe, set, update } = writable<AuthState>(initialState);

	return {
		subscribe,

		/** Llamar después de login/register exitoso para establecer la sesión */
		setSession(accessToken: string, refreshToken: string, user?: User) {
			setTokens(accessToken, refreshToken);
			update((s) => ({
				...s,
				accessToken,
				refreshToken,
				user: user ?? s.user,
				isAuthenticated: true,
				isLoading: false
			}));
		},

		/**
		 * Cargar el usuario desde /auth/me si hay token en localStorage.
		 * Se llama al iniciar la app para restaurar la sesión tras recarga.
		 * @returns true si el usuario se cargó correctamente, false si no había token o falló.
		 */
		async loadUser(): Promise<boolean> {
			if (!browser) return false;

			const token = localStorage.getItem('fc_access_token');
			if (!token) return false;

			update((s) => ({ ...s, isLoading: true }));
			try {
				const user = await getMe();
				update((s) => ({
					...s,
					user,
					accessToken: token,
					refreshToken: localStorage.getItem('fc_refresh_token'),
					isAuthenticated: true,
					isLoading: false
				}));
				return true;
			} catch {
				clearTokens();
				set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isLoading: false });
				return false;
			}
		},

		/** Cerrar sesión: limpiar tokens del store y localStorage */
		logout() {
			clearTokens();
			set({
				user: null,
				accessToken: null,
				refreshToken: null,
				isAuthenticated: false,
				isLoading: false
			});
		}
	};
}

export const authStore = createAuthStore();
export const isAuthenticated = derived(authStore, ($s) => $s.isAuthenticated);
export const currentUser = derived(authStore, ($s) => $s.user);
