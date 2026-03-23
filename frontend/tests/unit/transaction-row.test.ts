import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import TransactionRow from '$lib/components/transactions/TransactionRow.svelte';
import type { TransactionItem, AccountResponse, CategoryResponse } from '$lib/types';

const mockAccounts: AccountResponse[] = [
	{
		id: 'acc-1',
		user_id: 'u-1',
		name: 'N26',
		bank: 'N26',
		account_type: 'checking',
		currency: 'EUR',
		balance: 1000,
		is_active: true,
		created_at: '',
		updated_at: ''
	}
];

const mockCategories: CategoryResponse[] = [
	{
		id: 'cat-1',
		user_id: null,
		parent_id: null,
		name: 'Alimentación',
		color: null,
		icon: null,
		is_system: true,
		created_at: '',
		updated_at: ''
	}
];

function makeTx(overrides: Partial<TransactionItem> = {}): TransactionItem {
	return {
		id: 'tx-1',
		account_id: 'acc-1',
		amount: 45.32,
		description: 'MERCADONA SA',
		transaction_type: 'expense',
		date: '2026-03-23',
		category_id: 'cat-1',
		is_recurring: false,
		ml_suggested_category_id: null,
		ml_confidence: null,
		...overrides
	};
}

describe('TransactionRow', () => {
	it('muestra badge IA azul cuando confidence > 0.92 y es auto-asignada', () => {
		const tx = makeTx({
			category_id: 'cat-1',
			ml_suggested_category_id: 'cat-1',
			ml_confidence: 0.95
		});
		const { container } = render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		// El badge contiene "IA"
		const badge = container.querySelector('.badge');
		expect(badge?.textContent).toContain('IA');
	});

	it('muestra badge Sugerida cuando 0.5 < confidence <= 0.92', () => {
		const tx = makeTx({
			category_id: null,
			ml_suggested_category_id: 'cat-1',
			ml_confidence: 0.75
		});
		const { container } = render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		const badge = container.querySelector('.badge');
		expect(badge?.textContent).toContain('Sugerida');
	});

	it('no muestra badge cuando la transacción es manual (sin ML)', () => {
		const tx = makeTx({ ml_suggested_category_id: null, ml_confidence: null });
		const { container } = render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		const badge = container.querySelector('.badge');
		expect(badge).toBeNull();
	});

	it('muestra el importe en color verde para ingresos', () => {
		const tx = makeTx({ transaction_type: 'income', amount: 1200 });
		const { container } = render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		const amountEl = container.querySelector('.text-success-500');
		expect(amountEl).not.toBeNull();
		expect(amountEl?.textContent).toContain('+');
	});

	it('muestra el importe en color rojo para gastos', () => {
		const tx = makeTx({ transaction_type: 'expense', amount: 45.32 });
		const { container } = render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		const amountEl = container.querySelector('.text-error-500');
		expect(amountEl).not.toBeNull();
		expect(amountEl?.textContent).toContain('-');
	});

	it('muestra el nombre de la cuenta', () => {
		const tx = makeTx();
		render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		expect(screen.getByText('N26')).toBeTruthy();
	});

	it('muestra el nombre de la categoría asignada', () => {
		const tx = makeTx({ category_id: 'cat-1' });
		render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		expect(screen.getByText('Alimentación')).toBeTruthy();
	});

	it('muestra la descripción de la transacción', () => {
		const tx = makeTx({ description: 'MERCADONA SA' });
		render(TransactionRow, {
			props: { transaction: tx, accounts: mockAccounts, categories: mockCategories }
		});
		expect(screen.getByText('MERCADONA SA')).toBeTruthy();
	});
});
