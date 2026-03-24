import { test, expect } from '@playwright/test';

/**
 * Configura mocks de autenticación y APIs mínimas para simular una sesión activa.
 * Se usa en tests que necesitan navegar por rutas protegidas.
 */
async function setupAuthenticatedSession(page: import('@playwright/test').Page) {
	// Inyectar token en localStorage antes de que la página cargue
	await page.addInitScript(() => {
		localStorage.setItem('fc_access_token', 'fake-access-token');
		localStorage.setItem('fc_refresh_token', 'fake-refresh-token');
	});

	// Mock del endpoint de usuario autenticado
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

	// Mocks de APIs del dashboard para evitar errores de red
	await page.route('/api/v1/analytics/**', async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({})
		});
	});

	await page.route('/api/v1/budgets**', async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0 })
		});
	});

	await page.route('/api/v1/transactions**', async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 })
		});
	});
}

test.describe('Navegación (sesión autenticada)', () => {
	test('accede al dashboard con sesión activa', async ({ page }) => {
		await setupAuthenticatedSession(page);
		await page.goto('/dashboard');
		await expect(page).toHaveURL('/dashboard');
		// La AppBar con el título debe ser visible
		await expect(page.getByText('FinControl').first()).toBeVisible();
	});

	test('muestra el sidebar con los enlaces de navegación', async ({ page }) => {
		await setupAuthenticatedSession(page);
		await page.goto('/dashboard');

		await expect(page.getByRole('link', { name: /Dashboard/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /Transacciones/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /Presupuestos/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /Inversiones/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /Hipoteca/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /Predicciones/ })).toBeVisible();
		await expect(page.getByRole('link', { name: /Configuración/ })).toBeVisible();
	});

	test('navega de dashboard a transacciones', async ({ page }) => {
		await setupAuthenticatedSession(page);
		await page.goto('/dashboard');
		await page.getByRole('link', { name: /Transacciones/ }).click();
		await expect(page).toHaveURL('/transactions');
	});

	test('cierre de sesión redirige a login', async ({ page }) => {
		await setupAuthenticatedSession(page);
		await page.goto('/dashboard');
		await page.getByRole('button', { name: 'Salir' }).click();
		await expect(page).toHaveURL(/\/login/);
	});
});
