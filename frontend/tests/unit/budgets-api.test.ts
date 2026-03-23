import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetchJson: vi.fn(),
	apiFetch: vi.fn()
}));

describe('Budgets API', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('getBudgets sin parámetros construye la URL sin query params', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getBudgets } = await import('$lib/api/budgets');
		await getBudgets();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/budgets');
	});

	it('getBudgets con year y month construye la URL correctamente', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getBudgets } = await import('$lib/api/budgets');
		await getBudgets(2026, 3);

		const url = vi.mocked(apiFetchJson).mock.calls[0][0] as string;
		expect(url).toContain('period_year=2026');
		expect(url).toContain('period_month=3');
	});

	it('createBudget hace POST con el body correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		const mockBudget = { id: 'bud-1', category_id: 'cat-1', limit_amount: 500 };
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockBudget);

		const { createBudget } = await import('$lib/api/budgets');
		const result = await createBudget({
			category_id: 'cat-1',
			period_year: 2026,
			period_month: 3,
			limit_amount: 500
		});

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/budgets',
			expect.objectContaining({ method: 'POST' })
		);
		expect(result).toEqual(mockBudget);
	});

	it('updateBudget hace PATCH con el ID y body correctos', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ id: 'bud-1', limit_amount: 600 });

		const { updateBudget } = await import('$lib/api/budgets');
		await updateBudget('bud-1', { limit_amount: 600 });

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/budgets/bud-1',
			expect.objectContaining({ method: 'PATCH' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.limit_amount).toBe(600);
	});

	it('deleteBudget hace DELETE y resuelve si response.ok', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true } as Response);

		const { deleteBudget } = await import('$lib/api/budgets');
		await expect(deleteBudget('bud-1')).resolves.toBeUndefined();

		expect(apiFetch).toHaveBeenCalledWith('/api/v1/budgets/bud-1', { method: 'DELETE' });
	});

	it('deleteBudget lanza error si response no es ok', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: false } as Response);

		const { deleteBudget } = await import('$lib/api/budgets');
		await expect(deleteBudget('bud-1')).rejects.toThrow();
	});

	it('getBudgetStatuses construye la URL con year y month requeridos', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getBudgetStatuses } = await import('$lib/api/budgets');
		await getBudgetStatuses(2026, 3);

		const url = vi.mocked(apiFetchJson).mock.calls[0][0] as string;
		expect(url).toContain('/api/v1/budgets/status');
		expect(url).toContain('period_year=2026');
		expect(url).toContain('period_month=3');
	});

	it('markBudgetAlertRead hace PATCH al endpoint correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ id: 'alert-1', is_read: true });

		const { markBudgetAlertRead } = await import('$lib/api/budgets');
		const result = await markBudgetAlertRead('alert-1');

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/budgets/alerts/alert-1/read',
			expect.objectContaining({ method: 'PATCH' })
		);
		expect(result).toMatchObject({ is_read: true });
	});
});
