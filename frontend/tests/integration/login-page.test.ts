import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';

/**
 * Skeleton's TabGroup usa radio inputs ocultos (hidden div) para gestionar el estado.
 * fireEvent.click sobre el texto del tab no dispara el cambio del radio en jsdom.
 * Esta helper selecciona el radio input por su value y dispara el change event.
 */
async function clickTab(value: number) {
	const radio = document.querySelector(`input[type="radio"][value="${value}"]`) as HTMLInputElement;
	if (!radio) throw new Error(`Radio input con value="${value}" no encontrado`);
	radio.checked = true;
	await fireEvent.change(radio, { target: { checked: true, value: String(value) } });
}

// Mocks de la API
vi.mock('$lib/api/auth', () => ({
	login: vi.fn(),
	register: vi.fn()
}));

vi.mock('$lib/api/client', () => ({
	setTokens: vi.fn(),
	clearTokens: vi.fn(),
	getAccessToken: vi.fn(() => null),
	getRefreshToken: vi.fn(() => null),
	apiFetch: vi.fn(),
	apiFetchJson: vi.fn()
}));

vi.mock('$lib/stores/auth', () => ({
	authStore: {
		loadUser: vi.fn().mockResolvedValue(true),
		setSession: vi.fn(),
		logout: vi.fn()
	},
	isAuthenticated: { subscribe: vi.fn(() => () => {}) },
	currentUser: { subscribe: vi.fn(() => () => {}) }
}));

describe('Login Page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		localStorage.clear();
	});

	it('renderiza los tabs de login y registro', async () => {
		const LoginPage = (await import('../../src/routes/login/+page.svelte')).default;
		render(LoginPage);

		expect(screen.getByText('Iniciar sesión')).toBeInTheDocument();
		expect(screen.getByText('Registrarse')).toBeInTheDocument();
	});

	it('renderiza el formulario de login por defecto', async () => {
		const LoginPage = (await import('../../src/routes/login/+page.svelte')).default;
		render(LoginPage);

		expect(screen.getByPlaceholderText('usuario@ejemplo.com')).toBeInTheDocument();
		expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
		expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument();
	});

	it('muestra error cuando el login falla', async () => {
		const { login } = await import('$lib/api/auth');
		vi.mocked(login).mockRejectedValueOnce(new Error('Credenciales incorrectas'));

		const LoginPage = (await import('../../src/routes/login/+page.svelte')).default;
		render(LoginPage);

		const emailInput = screen.getByPlaceholderText('usuario@ejemplo.com');
		const passwordInput = screen.getByPlaceholderText('••••••••');

		await fireEvent.input(emailInput, { target: { value: 'bad@test.com' } });
		await fireEvent.input(passwordInput, { target: { value: 'wrongpass' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Entrar' }));

		await waitFor(() => {
			expect(screen.getByRole('alert')).toHaveTextContent('Credenciales incorrectas');
		});
	});

	it('llama a goto con /dashboard tras login exitoso', async () => {
		const { goto } = await import('$app/navigation');
		const { login } = await import('$lib/api/auth');
		vi.mocked(login).mockResolvedValueOnce({
			access_token: 'tok',
			refresh_token: 'ref',
			token_type: 'bearer'
		});

		const LoginPage = (await import('../../src/routes/login/+page.svelte')).default;
		render(LoginPage);

		await fireEvent.input(screen.getByPlaceholderText('usuario@ejemplo.com'), {
			target: { value: 'user@test.com' }
		});
		await fireEvent.input(screen.getByPlaceholderText('••••••••'), {
			target: { value: 'password123' }
		});
		await fireEvent.click(screen.getByRole('button', { name: 'Entrar' }));

		await waitFor(() => {
			expect(goto).toHaveBeenCalledWith('/dashboard');
		});
	});

	it('cambia al formulario de registro al hacer click en la tab', async () => {
		const LoginPage = (await import('../../src/routes/login/+page.svelte')).default;
		render(LoginPage);

		// El TabGroup de Skeleton usa radio inputs ocultos; hay que disparar change sobre el radio
		await clickTab(1);

		await waitFor(() => {
			expect(screen.getByPlaceholderText('Mínimo 8 caracteres')).toBeInTheDocument();
			expect(screen.getByPlaceholderText('Repite la contraseña')).toBeInTheDocument();
		});
	});

	it('muestra error si las contraseñas no coinciden en registro', async () => {
		const LoginPage = (await import('../../src/routes/login/+page.svelte')).default;
		render(LoginPage);

		await clickTab(1);

		await waitFor(async () => {
			const emailInput = screen.getByPlaceholderText('usuario@ejemplo.com');
			const passInput = screen.getByPlaceholderText('Mínimo 8 caracteres');
			const confirmInput = screen.getByPlaceholderText('Repite la contraseña');

			await fireEvent.input(emailInput, { target: { value: 'new@test.com' } });
			await fireEvent.input(passInput, { target: { value: 'password123' } });
			await fireEvent.input(confirmInput, { target: { value: 'password456' } });
			await fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
		});

		await waitFor(() => {
			expect(screen.getByRole('alert')).toHaveTextContent('Las contraseñas no coinciden');
		});
	});

	it('muestra error si la contraseña tiene menos de 8 caracteres en registro', async () => {
		const LoginPage = (await import('../../src/routes/login/+page.svelte')).default;
		render(LoginPage);

		await clickTab(1);

		await waitFor(async () => {
			await fireEvent.input(screen.getByPlaceholderText('usuario@ejemplo.com'), {
				target: { value: 'new@test.com' }
			});
			await fireEvent.input(screen.getByPlaceholderText('Mínimo 8 caracteres'), {
				target: { value: 'short' }
			});
			await fireEvent.input(screen.getByPlaceholderText('Repite la contraseña'), {
				target: { value: 'short' }
			});
			await fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
		});

		await waitFor(() => {
			expect(screen.getByRole('alert')).toHaveTextContent('al menos 8 caracteres');
		});
	});
});
