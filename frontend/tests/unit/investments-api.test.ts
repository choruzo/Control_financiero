import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetchJson: vi.fn(),
	apiFetch: vi.fn()
}));

describe('Investments API', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('getInvestmentSummary llama al endpoint correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ total_investments: 3 });

		const { getInvestmentSummary } = await import('$lib/api/investments');
		const result = await getInvestmentSummary();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/investments/summary');
		expect(result).toMatchObject({ total_investments: 3 });
	});

	it('getInvestments sin filtros construye la URL sin query params', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getInvestments } = await import('$lib/api/investments');
		await getInvestments();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/investments');
	});

	it('getInvestments con filtro investment_type construye la URL correctamente', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getInvestments } = await import('$lib/api/investments');
		await getInvestments({ investment_type: 'deposit', is_active: true });

		const url = vi.mocked(apiFetchJson).mock.calls[0][0] as string;
		expect(url).toContain('investment_type=deposit');
		expect(url).toContain('is_active=true');
	});

	it('getInvestmentStatus llama al endpoint con el ID correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		const mockStatus = { investment: { id: 'inv-1' }, return_percentage: 4.5 };
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockStatus);

		const { getInvestmentStatus } = await import('$lib/api/investments');
		const result = await getInvestmentStatus('inv-1');

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/investments/inv-1/status');
		expect(result).toMatchObject({ return_percentage: 4.5 });
	});

	it('createInvestment hace POST con el body correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		const mockInv = { id: 'inv-1', name: 'Depósito 2025' };
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockInv);

		const { createInvestment } = await import('$lib/api/investments');
		const result = await createInvestment({
			name: 'Depósito 2025',
			investment_type: 'deposit',
			principal_amount: 10000,
			interest_rate: 4.25,
			interest_type: 'simple',
			start_date: '2025-01-01'
		});

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/investments',
			expect.objectContaining({ method: 'POST' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.principal_amount).toBe(10000);
		expect(result).toEqual(mockInv);
	});

	it('updateInvestment hace PATCH con el ID y body correctos', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ id: 'inv-1', interest_rate: 4.5 });

		const { updateInvestment } = await import('$lib/api/investments');
		await updateInvestment('inv-1', { interest_rate: 4.5 });

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/investments/inv-1',
			expect.objectContaining({ method: 'PATCH' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.interest_rate).toBe(4.5);
	});

	it('deleteInvestment hace DELETE y resuelve si response.ok', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true } as Response);

		const { deleteInvestment } = await import('$lib/api/investments');
		await expect(deleteInvestment('inv-1')).resolves.toBeUndefined();

		expect(apiFetch).toHaveBeenCalledWith('/api/v1/investments/inv-1', { method: 'DELETE' });
	});

	it('renewInvestment hace POST al endpoint de renovación', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ id: 'inv-1', renewals_count: 1 });

		const { renewInvestment } = await import('$lib/api/investments');
		const result = await renewInvestment('inv-1');

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/investments/inv-1/renew',
			expect.objectContaining({ method: 'POST' })
		);
		expect(result).toMatchObject({ renewals_count: 1 });
	});
});
