// Auth
export interface Token {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

export interface User {
	id: string; // UUID como string
	email: string;
	is_active: boolean;
	created_at: string; // ISO 8601
}

export interface UserCreate {
	email: string;
	password: string;
}

// Estado de autenticación para el store
export interface AuthState {
	user: User | null;
	accessToken: string | null;
	refreshToken: string | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

// Respuesta de error de la API
export interface ApiErrorResponse {
	detail: string | ValidationError[];
}

export interface ValidationError {
	loc: (string | number)[];
	msg: string;
	type: string;
}
