import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetchJson: vi.fn(),
	apiFetch: vi.fn()
}));

describe('Tax API', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('getTaxBrackets sin filtros llama al endpoint correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getTaxBrackets } = await import('$lib/api/tax');
		await getTaxBrackets();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/tax/brackets');
	});

	it('getTaxBrackets con year y bracket_type construye query params correctos', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([]);

		const { getTaxBrackets } = await import('$lib/api/tax');
		await getTaxBrackets(2025, 'general');

		const url = vi.mocked(apiFetchJson).mock.calls[0][0] as string;
		expect(url).toContain('year=2025');
		expect(url).toContain('bracket_type=general');
	});

	it('getTaxConfigs llama al endpoint correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce([{ id: 'cfg-1', tax_year: 2025 }]);

		const { getTaxConfigs } = await import('$lib/api/tax');
		const result = await getTaxConfigs();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/tax/configs');
		expect(result).toHaveLength(1);
	});

	it('createTaxConfig hace POST con el body correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ id: 'cfg-1', tax_year: 2025, gross_annual_salary: 35000 });

		const { createTaxConfig } = await import('$lib/api/tax');
		const result = await createTaxConfig({ tax_year: 2025, gross_annual_salary: 35000 });

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/tax/configs',
			expect.objectContaining({ method: 'POST' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.tax_year).toBe(2025);
		expect(body.gross_annual_salary).toBe(35000);
		expect(result.id).toBe('cfg-1');
	});

	it('updateTaxConfig hace PATCH con el ID y body correctos', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ id: 'cfg-1', gross_annual_salary: 40000 });

		const { updateTaxConfig } = await import('$lib/api/tax');
		await updateTaxConfig('cfg-1', { gross_annual_salary: 40000 });

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/tax/configs/cfg-1',
			expect.objectContaining({ method: 'PATCH' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.gross_annual_salary).toBe(40000);
	});

	it('deleteTaxConfig hace DELETE y resuelve si response.ok', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true } as Response);

		const { deleteTaxConfig } = await import('$lib/api/tax');
		await expect(deleteTaxConfig('cfg-1')).resolves.toBeUndefined();

		expect(apiFetch).toHaveBeenCalledWith('/api/v1/tax/configs/cfg-1', { method: 'DELETE' });
	});

	it('getTaxCalculation llama al endpoint de cálculo y devuelve el breakdown', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		const mockCalc = {
			tax_year: 2025,
			gross_annual: 35000,
			ss_annual: 2222.5,
			ss_rate: 0.0635,
			work_expenses_deduction: 2000,
			taxable_base: 30777.5,
			irpf_annual: 5800,
			effective_rate: 0.1886,
			net_annual: 26977.5,
			net_monthly: 2248.13,
			bracket_breakdown: [{ rate: 0.19, taxable_in_bracket: 12450, tax_in_bracket: 2365.5 }]
		};
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockCalc);

		const { getTaxCalculation } = await import('$lib/api/tax');
		const result = await getTaxCalculation('cfg-1');

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/tax/configs/cfg-1/calculation');
		expect(result.net_monthly).toBe(2248.13);
		expect(result.bracket_breakdown).toHaveLength(1);
	});
});
