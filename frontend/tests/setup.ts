import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock de módulos SvelteKit que no existen en el entorno de test (jsdom)
vi.mock('$app/environment', () => ({
	browser: true
}));

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

vi.mock('$app/stores', () => {
	const { readable } = require('svelte/store');
	return {
		page: readable({
			url: new URL('http://localhost:3000/login'),
			params: {},
			route: { id: '/login' },
			status: 200,
			error: null,
			data: {},
			form: null
		})
	};
});
