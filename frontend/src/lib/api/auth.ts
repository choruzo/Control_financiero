import { browser } from '$app/environment';
import { apiFetchJson } from './client';
import type { Token, User, UserCreate } from '$lib/types';

// URL base para llamadas directas sin el interceptor (login, refresh)
const API_BASE = browser
	? (import.meta.env.VITE_API_URL ?? 'http://localhost:8000')
	: 'http://backend:8000';

/**
 * Login de usuario.
 * CRÍTICO: el backend usa OAuth2PasswordRequestForm → FormData con campo 'username' (no 'email').
 * Enviar JSON da 422 Unprocessable Entity.
 */
export async function login(email: string, password: string): Promise<Token> {
	const formData = new FormData();
	formData.append('username', email); // El campo se llama 'username' aunque sea un email
	formData.append('password', password);

	const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
		method: 'POST',
		body: formData
		// NO establecer Content-Type: el browser calcula el boundary de multipart
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Credenciales incorrectas' }));
		const message = typeof error.detail === 'string' ? error.detail : 'Credenciales incorrectas';
		throw new Error(message);
	}

	return response.json() as Promise<Token>;
}

/**
 * Registro de nuevo usuario con JSON (no FormData).
 */
export async function register(data: UserCreate): Promise<Token> {
	return apiFetchJson<Token>('/api/v1/auth/register', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

/**
 * Obtener el usuario autenticado actual.
 * Requiere token Bearer válido en el store/localStorage.
 */
export async function getMe(): Promise<User> {
	return apiFetchJson<User>('/api/v1/auth/me');
}

/**
 * Renovar par de tokens usando el refresh token.
 * Llamada directa sin interceptor para evitar bucle infinito.
 */
export async function refreshTokens(refreshToken: string): Promise<Token> {
	const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ refresh_token: refreshToken })
	});

	if (!response.ok) {
		throw new Error('No se pudo renovar la sesión');
	}

	return response.json() as Promise<Token>;
}
