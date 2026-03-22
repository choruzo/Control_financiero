import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Importar los módulos bajo test DESPUÉS de configurar los mocks
let apiFetch: typeof import('$lib/api/client').apiFetch;
let setTokens: typeof import('$lib/api/client').setTokens;
let clearTokens: typeof import('$lib/api/client').clearTokens;
let getAccessToken: typeof import('$lib/api/client').getAccessToken;

describe('API Client', () => {
	beforeEach(async () => {
		// Limpiar localStorage antes de cada test
		localStorage.clear();
		vi.clearAllMocks();

		// Reimportar para que el módulo lea el estado actualizado de localStorage
		vi.resetModules();
		const mod = await import('$lib/api/client');
		apiFetch = mod.apiFetch;
		setTokens = mod.setTokens;
		clearTokens = mod.clearTokens;
		getAccessToken = mod.getAccessToken;
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('setTokens / clearTokens / getAccessToken', () => {
		it('setTokens guarda tokens en localStorage', () => {
			setTokens('access-123', 'refresh-456');
			expect(localStorage.getItem('fc_access_token')).toBe('access-123');
			expect(localStorage.getItem('fc_refresh_token')).toBe('refresh-456');
		});

		it('clearTokens elimina ambos tokens', () => {
			setTokens('access-123', 'refresh-456');
			clearTokens();
			expect(localStorage.getItem('fc_access_token')).toBeNull();
			expect(localStorage.getItem('fc_refresh_token')).toBeNull();
		});

		it('getAccessToken devuelve null cuando no hay token', () => {
			expect(getAccessToken()).toBeNull();
		});

		it('getAccessToken devuelve el token guardado', () => {
			localStorage.setItem('fc_access_token', 'my-token');
			expect(getAccessToken()).toBe('my-token');
		});
	});

	describe('apiFetch — adjuntar Authorization header', () => {
		it('adjunta Bearer token cuando hay token en localStorage', async () => {
			localStorage.setItem('fc_access_token', 'valid-token');
			const mockFetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
			vi.stubGlobal('fetch', mockFetch);

			await apiFetch('/api/v1/test');

			const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = new Headers(options.headers as HeadersInit);
			expect(headers.get('Authorization')).toBe('Bearer valid-token');
		});

		it('no adjunta Authorization cuando no hay token', async () => {
			const mockFetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
			vi.stubGlobal('fetch', mockFetch);

			await apiFetch('/api/v1/test');

			const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = new Headers(options.headers as HeadersInit);
			expect(headers.get('Authorization')).toBeNull();
		});

		it('establece Content-Type application/json por defecto', async () => {
			const mockFetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
			vi.stubGlobal('fetch', mockFetch);

			await apiFetch('/api/v1/test', { method: 'POST', body: '{}' });

			const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = new Headers(options.headers as HeadersInit);
			expect(headers.get('Content-Type')).toBe('application/json');
		});

		it('no sobreescribe Content-Type cuando se pasa FormData', async () => {
			const mockFetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
			vi.stubGlobal('fetch', mockFetch);
			const formData = new FormData();
			formData.append('username', 'test@test.com');

			await apiFetch('/api/v1/auth/login', { method: 'POST', body: formData });

			const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
			const headers = new Headers(options.headers as HeadersInit);
			// El browser gestiona Content-Type para FormData; no debe estar forzado
			expect(headers.get('Content-Type')).toBeNull();
		});
	});

	describe('apiFetch — interceptor 401 y refresh', () => {
		it('reintenta con nuevo token tras 401 + refresh exitoso', async () => {
			localStorage.setItem('fc_access_token', 'old-token');
			localStorage.setItem('fc_refresh_token', 'refresh-token');

			const mockFetch = vi
				.fn()
				// Primera llamada → 401
				.mockResolvedValueOnce(new Response('Unauthorized', { status: 401 }))
				// Llamada al refresh endpoint → 200 con nuevos tokens
				.mockResolvedValueOnce(
					new Response(
						JSON.stringify({ access_token: 'new-token', refresh_token: 'new-refresh' }),
						{ status: 200, headers: { 'Content-Type': 'application/json' } }
					)
				)
				// Reintento de la request original → 200
				.mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }));

			vi.stubGlobal('fetch', mockFetch);

			const response = await apiFetch('/api/v1/resource');

			expect(response.status).toBe(200);
			// fetch debe haberse llamado 3 veces: original + refresh + retry
			expect(mockFetch).toHaveBeenCalledTimes(3);
			// El nuevo token debe estar en localStorage
			expect(localStorage.getItem('fc_access_token')).toBe('new-token');
		});

		it('limpia tokens y redirige a /login si el refresh falla', async () => {
			const { goto } = await import('$app/navigation');
			localStorage.setItem('fc_access_token', 'old-token');
			localStorage.setItem('fc_refresh_token', 'bad-refresh');

			const mockFetch = vi
				.fn()
				.mockResolvedValueOnce(new Response('Unauthorized', { status: 401 }))
				.mockResolvedValueOnce(new Response('Forbidden', { status: 403 }));

			vi.stubGlobal('fetch', mockFetch);

			await apiFetch('/api/v1/resource');

			expect(localStorage.getItem('fc_access_token')).toBeNull();
			expect(localStorage.getItem('fc_refresh_token')).toBeNull();
			expect(goto).toHaveBeenCalledWith('/login');
		});

		it('no duplica el refresh con dos peticiones 401 concurrentes', async () => {
			localStorage.setItem('fc_access_token', 'old-token');
			localStorage.setItem('fc_refresh_token', 'refresh-token');

			let refreshCallCount = 0;
			const mockFetch = vi.fn().mockImplementation((url: string) => {
				if ((url as string).includes('/auth/refresh')) {
					refreshCallCount++;
					return Promise.resolve(
						new Response(
							JSON.stringify({ access_token: 'new-token', refresh_token: 'new-refresh' }),
							{ status: 200, headers: { 'Content-Type': 'application/json' } }
						)
					);
				}
				return Promise.resolve(new Response('Unauthorized', { status: 401 }));
			});

			vi.stubGlobal('fetch', mockFetch);

			// Dos peticiones simultáneas
			await Promise.all([apiFetch('/api/v1/res1'), apiFetch('/api/v1/res2')]);

			// El refresh debe haberse llamado exactamente una vez, no dos
			expect(refreshCallCount).toBe(1);
		});
	});
});
