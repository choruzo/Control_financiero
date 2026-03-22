import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

// Mock de getMe para controlar su comportamiento en tests
vi.mock('$lib/api/auth', () => ({
	getMe: vi.fn()
}));

describe('Auth Store', () => {
	beforeEach(() => {
		localStorage.clear();
		vi.clearAllMocks();
		// Resetear módulos para que el store parta de estado limpio
		vi.resetModules();
	});

	it('setSession actualiza el store y guarda tokens en localStorage', async () => {
		const { authStore, isAuthenticated, currentUser } = await import('$lib/stores/auth');

		authStore.setSession('access-tok', 'refresh-tok');

		expect(localStorage.getItem('fc_access_token')).toBe('access-tok');
		expect(localStorage.getItem('fc_refresh_token')).toBe('refresh-tok');
		expect(get(isAuthenticated)).toBe(true);
	});

	it('setSession con usuario actualiza currentUser', async () => {
		const { authStore, currentUser } = await import('$lib/stores/auth');
		const mockUser = { id: 'uuid-1', email: 'test@test.com', is_active: true, created_at: '2025-01-01T00:00:00Z' };

		authStore.setSession('access-tok', 'refresh-tok', mockUser);

		expect(get(currentUser)).toEqual(mockUser);
	});

	it('logout limpia el store y localStorage', async () => {
		const { authStore, isAuthenticated, currentUser } = await import('$lib/stores/auth');

		authStore.setSession('access-tok', 'refresh-tok');
		authStore.logout();

		expect(localStorage.getItem('fc_access_token')).toBeNull();
		expect(localStorage.getItem('fc_refresh_token')).toBeNull();
		expect(get(isAuthenticated)).toBe(false);
		expect(get(currentUser)).toBeNull();
	});

	it('loadUser carga el usuario desde /auth/me si hay token', async () => {
		const { getMe } = await import('$lib/api/auth');
		const mockUser = { id: 'uuid-1', email: 'user@test.com', is_active: true, created_at: '2025-01-01T00:00:00Z' };
		vi.mocked(getMe).mockResolvedValueOnce(mockUser);

		localStorage.setItem('fc_access_token', 'valid-token');
		localStorage.setItem('fc_refresh_token', 'valid-refresh');

		const { authStore, isAuthenticated, currentUser } = await import('$lib/stores/auth');
		const result = await authStore.loadUser();

		expect(result).toBe(true);
		expect(get(isAuthenticated)).toBe(true);
		expect(get(currentUser)).toEqual(mockUser);
	});

	it('loadUser devuelve false y limpia si no hay token', async () => {
		const { authStore, isAuthenticated } = await import('$lib/stores/auth');
		const result = await authStore.loadUser();

		expect(result).toBe(false);
		expect(get(isAuthenticated)).toBe(false);
	});

	it('loadUser llama logout si getMe falla', async () => {
		const { getMe } = await import('$lib/api/auth');
		vi.mocked(getMe).mockRejectedValueOnce(new Error('Unauthorized'));

		localStorage.setItem('fc_access_token', 'expired-token');

		const { authStore, isAuthenticated } = await import('$lib/stores/auth');
		const result = await authStore.loadUser();

		expect(result).toBe(false);
		expect(get(isAuthenticated)).toBe(false);
		expect(localStorage.getItem('fc_access_token')).toBeNull();
	});

	it('isAuthenticated derivado refleja el estado correcto', async () => {
		const { authStore, isAuthenticated } = await import('$lib/stores/auth');

		expect(get(isAuthenticated)).toBe(false);
		authStore.setSession('tok', 'ref');
		expect(get(isAuthenticated)).toBe(true);
		authStore.logout();
		expect(get(isAuthenticated)).toBe(false);
	});
});
