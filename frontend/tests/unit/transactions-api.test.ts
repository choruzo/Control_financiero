import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetchJson: vi.fn(),
	apiFetch: vi.fn()
}));

describe('Transactions API', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		vi.resetModules();
	});

	it('getTransactions sin filtros construye la URL sin query params', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ items: [], total: 0, page: 1, per_page: 50, pages: 0 });

		const { getTransactions } = await import('$lib/api/transactions');
		await getTransactions();

		expect(apiFetchJson).toHaveBeenCalledWith('/api/v1/transactions');
	});

	it('getTransactions con filtros construye la URL correctamente', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ items: [], total: 0, page: 1, per_page: 50, pages: 0 });

		const { getTransactions } = await import('$lib/api/transactions');
		await getTransactions({
			date_from: '2026-01-01',
			category_id: 'cat-uuid',
			transaction_type: 'expense',
			page: 2
		});

		const call = vi.mocked(apiFetchJson).mock.calls[0][0] as string;
		expect(call).toContain('date_from=2026-01-01');
		expect(call).toContain('category_id=cat-uuid');
		expect(call).toContain('transaction_type=expense');
		expect(call).toContain('page=2');
	});

	it('createTransaction hace POST con el body correcto', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		const mockTx = { id: 'tx-123', amount: 50, description: 'Test' };
		vi.mocked(apiFetchJson).mockResolvedValueOnce(mockTx);

		const { createTransaction } = await import('$lib/api/transactions');
		const result = await createTransaction({
			account_id: 'acc-uuid',
			amount: 50,
			description: 'Test',
			transaction_type: 'expense',
			date: '2026-03-23'
		});

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/transactions',
			expect.objectContaining({ method: 'POST' })
		);
		expect(result).toEqual(mockTx);
	});

	it('updateTransaction hace PATCH con el ID y body correctos', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ id: 'tx-123' });

		const { updateTransaction } = await import('$lib/api/transactions');
		await updateTransaction('tx-123', { category_id: 'cat-uuid' });

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/transactions/tx-123',
			expect.objectContaining({ method: 'PATCH' })
		);
	});

	it('deleteTransaction hace DELETE y no lanza si response.ok', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: true } as Response);

		const { deleteTransaction } = await import('$lib/api/transactions');
		await expect(deleteTransaction('tx-123')).resolves.toBeUndefined();

		expect(apiFetch).toHaveBeenCalledWith('/api/v1/transactions/tx-123', { method: 'DELETE' });
	});

	it('deleteTransaction lanza error si response no es ok', async () => {
		const { apiFetch } = await import('$lib/api/client');
		vi.mocked(apiFetch).mockResolvedValueOnce({ ok: false } as Response);

		const { deleteTransaction } = await import('$lib/api/transactions');
		await expect(deleteTransaction('tx-123')).rejects.toThrow();
	});

	it('importCsv envía FormData con dry_run=true', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ imported: 5, dry_run: true });

		const { importCsv } = await import('$lib/api/transactions');
		const file = new File(['csv content'], 'test.csv', { type: 'text/csv' });
		const result = await importCsv(file, 'acc-uuid', true);

		const call = vi.mocked(apiFetchJson).mock.calls[0];
		expect(call[0]).toContain('dry_run=true');
		expect(call[0]).toContain('account_id=acc-uuid');
		expect(call[1]?.body).toBeInstanceOf(FormData);
		expect(result).toMatchObject({ dry_run: true });
	});

	it('importCsv envía dry_run=false al confirmar', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({ imported: 5, dry_run: false });

		const { importCsv } = await import('$lib/api/transactions');
		const file = new File(['csv content'], 'test.csv', { type: 'text/csv' });
		await importCsv(file, 'acc-uuid', false);

		const call = vi.mocked(apiFetchJson).mock.calls[0];
		expect(call[0]).toContain('dry_run=false');
	});

	it('sendMlFeedback hace POST con los parámetros correctos', async () => {
		const { apiFetchJson } = await import('$lib/api/client');
		vi.mocked(apiFetchJson).mockResolvedValueOnce({});

		const { sendMlFeedback } = await import('$lib/api/transactions');
		await sendMlFeedback('tx-uuid', 'orig-cat-uuid', 'correct-cat-uuid', 0.75);

		expect(apiFetchJson).toHaveBeenCalledWith(
			'/api/v1/ml/feedback',
			expect.objectContaining({ method: 'POST' })
		);
		const body = JSON.parse(vi.mocked(apiFetchJson).mock.calls[0][1]!.body as string);
		expect(body.transaction_id).toBe('tx-uuid');
		expect(body.original_category_id).toBe('orig-cat-uuid');
		expect(body.correct_category_id).toBe('correct-cat-uuid');
		expect(body.confidence).toBe(0.75);
	});
});
