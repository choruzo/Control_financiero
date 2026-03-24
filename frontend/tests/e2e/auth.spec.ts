import { test, expect } from '@playwright/test';

test.describe('Autenticación', () => {
	test('muestra el formulario de login', async ({ page }) => {
		await page.goto('/login');
		await expect(page.locator('h1')).toContainText('FinControl');
		await expect(page.locator('input[type="email"]')).toBeVisible();
		await expect(page.locator('input[type="password"]')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible();
	});

	test('muestra las pestañas de login y registro', async ({ page }) => {
		await page.goto('/login');
		await expect(page.getByRole('tab', { name: 'Iniciar sesión' })).toBeVisible();
		await expect(page.getByRole('tab', { name: 'Registrarse' })).toBeVisible();
	});

	test('redirige a /login cuando no hay sesión activa', async ({ page }) => {
		await page.goto('/dashboard');
		await expect(page).toHaveURL(/\/login/);
	});

	test('redirige a /login desde cualquier ruta protegida sin sesión', async ({ page }) => {
		for (const route of ['/transactions', '/budgets', '/investments', '/mortgage', '/predictions', '/settings']) {
			await page.goto(route);
			await expect(page).toHaveURL(/\/login/);
		}
	});

	test('muestra error al intentar login con credenciales incorrectas', async ({ page }) => {
		await page.route('/api/v1/auth/login', async (route) => {
			await route.fulfill({
				status: 401,
				contentType: 'application/json',
				body: JSON.stringify({ detail: 'Credenciales incorrectas' })
			});
		});

		await page.goto('/login');
		await page.locator('input[type="email"]').fill('usuario@test.com');
		await page.locator('input[type="password"]').fill('contraseña-incorrecta');
		await page.getByRole('button', { name: 'Entrar' }).click();

		await expect(page.locator('[role="alert"]')).toBeVisible();
	});

	test('login exitoso redirige al dashboard', async ({ page }) => {
		await page.route('/api/v1/auth/login', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					access_token: 'fake-access-token',
					refresh_token: 'fake-refresh-token',
					token_type: 'bearer'
				})
			});
		});

		await page.route('/api/v1/auth/me', async (route) => {
			await route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({
					id: 1,
					email: 'usuario@test.com',
					created_at: '2026-01-01T00:00:00Z'
				})
			});
		});

		await page.goto('/login');
		await page.locator('input[type="email"]').fill('usuario@test.com');
		await page.locator('input[type="password"]').fill('contraseñaSegura123');
		await page.getByRole('button', { name: 'Entrar' }).click();

		await expect(page).toHaveURL('/dashboard', { timeout: 10_000 });
	});
});
