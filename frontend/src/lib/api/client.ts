import { browser } from '$app/environment';

// En el browser usamos la variable de entorno inyectada por Vite.
// En el servidor Node (SSR desactivado, pero por si acaso) usamos el nombre de servicio Docker.
const API_BASE = browser
	? (import.meta.env.VITE_API_URL ?? 'http://localhost:8000')
	: 'http://backend:8000';

// ── Mutex de refresh ──────────────────────────────────────────────────────────
// Evita que múltiples peticiones simultáneas con 401 disparen varios refresh.
type RefreshCallback = (token: string | null) => void;
let isRefreshing = false;
let refreshQueue: RefreshCallback[] = [];

function processQueue(token: string | null): void {
	refreshQueue.forEach((cb) => cb(token));
	refreshQueue = [];
}

// ── Gestión de tokens en localStorage ────────────────────────────────────────
export function getAccessToken(): string | null {
	if (!browser) return null;
	return localStorage.getItem('fc_access_token');
}

export function getRefreshToken(): string | null {
	if (!browser) return null;
	return localStorage.getItem('fc_refresh_token');
}

export function setTokens(accessToken: string, refreshToken: string): void {
	if (!browser) return;
	localStorage.setItem('fc_access_token', accessToken);
	localStorage.setItem('fc_refresh_token', refreshToken);
}

export function clearTokens(): void {
	if (!browser) return;
	localStorage.removeItem('fc_access_token');
	localStorage.removeItem('fc_refresh_token');
}

// ── Intento de refresh ────────────────────────────────────────────────────────
async function attemptRefresh(): Promise<string | null> {
	const refreshToken = getRefreshToken();
	if (!refreshToken) return null;

	try {
		const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ refresh_token: refreshToken })
		});

		if (!response.ok) {
			clearTokens();
			return null;
		}

		const data = await response.json();
		setTokens(data.access_token, data.refresh_token);
		return data.access_token as string;
	} catch {
		clearTokens();
		return null;
	}
}

// ── Fetch principal con interceptor 401 → refresh → retry ────────────────────
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
	const url = `${API_BASE}${path}`;
	const token = getAccessToken();

	const headers = new Headers(options.headers);
	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	// No sobreescribir Content-Type si es FormData (el browser calcula el boundary)
	if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
		headers.set('Content-Type', 'application/json');
	}

	const response = await fetch(url, { ...options, headers });

	// Si no es 401, devolver directamente
	if (response.status !== 401) {
		return response;
	}

	// ── Lógica de cola para refresh concurrente ───────────────────────────────
	if (isRefreshing) {
		// Encolar y esperar al refresh ya en curso
		return new Promise<Response>((resolve, reject) => {
			refreshQueue.push(async (newToken) => {
				if (!newToken) {
					reject(new Error('Sesión expirada'));
					return;
				}
				const retryHeaders = new Headers(headers);
				retryHeaders.set('Authorization', `Bearer ${newToken}`);
				resolve(fetch(url, { ...options, headers: retryHeaders }));
			});
		});
	}

	isRefreshing = true;
	const newToken = await attemptRefresh();
	isRefreshing = false;
	processQueue(newToken);

	if (!newToken) {
		// Redirigir al login importando goto dinámicamente (evita dependencias circulares en tests)
		if (browser) {
			const { goto } = await import('$app/navigation');
			await goto('/login');
		}
		return response; // devolver la respuesta 401 original
	}

	// Reintentar la request original con el nuevo token
	const retryHeaders = new Headers(headers);
	retryHeaders.set('Authorization', `Bearer ${newToken}`);
	return fetch(url, { ...options, headers: retryHeaders });
}

// ── Helper para peticiones JSON que lanza en error HTTP ───────────────────────
export async function apiFetchJson<T>(path: string, options: RequestInit = {}): Promise<T> {
	const response = await apiFetch(path, options);
	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
		const message = typeof error.detail === 'string' ? error.detail : 'Error de validación';
		throw new ApiError(response.status, message);
	}
	return response.json() as Promise<T>;
}

export class ApiError extends Error {
	constructor(
		public readonly status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}
