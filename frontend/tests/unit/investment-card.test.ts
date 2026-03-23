import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import InvestmentCard from '$lib/components/investments/InvestmentCard.svelte';
import type { InvestmentResponse } from '$lib/types';

// getInvestmentStatus se llama en onMount vía dynamic import — mockear el módulo
vi.mock('$lib/api/investments', () => ({
	getInvestmentStatus: vi.fn().mockResolvedValue({
		investment: {},
		accrued_interest: 100,
		total_return: 100,
		return_percentage: 1.0,
		days_held: 90,
		days_to_maturity: null
	})
}));

function makeInvestment(overrides: Partial<InvestmentResponse> = {}): InvestmentResponse {
	return {
		id: 'inv-1',
		user_id: 'user-1',
		account_id: null,
		name: 'Depósito 2025',
		investment_type: 'deposit',
		principal_amount: 10000,
		interest_rate: 4.25,
		interest_type: 'simple',
		compounding_frequency: null,
		current_value: null,
		start_date: '2025-01-01',
		maturity_date: null,
		auto_renew: false,
		renewal_period_months: null,
		renewals_count: 0,
		notes: null,
		is_active: true,
		created_at: '',
		updated_at: '',
		...overrides
	};
}

describe('InvestmentCard', () => {
	it('muestra el nombre de la inversión', () => {
		render(InvestmentCard, { props: { investment: makeInvestment() } });
		expect(screen.getByText('Depósito 2025')).toBeInTheDocument();
	});

	it('muestra el badge de tipo correcto para deposit', () => {
		render(InvestmentCard, { props: { investment: makeInvestment({ investment_type: 'deposit' }) } });
		expect(screen.getByText('Depósito')).toBeInTheDocument();
	});

	it('muestra el badge de tipo correcto para fund', () => {
		render(InvestmentCard, { props: { investment: makeInvestment({ investment_type: 'fund', name: 'Fondo X' }) } });
		expect(screen.getByText('Fondo')).toBeInTheDocument();
	});

	it('muestra badge "Vence pronto" cuando el vencimiento es en ≤30 días', () => {
		const soon = new Date();
		soon.setDate(soon.getDate() + 10);
		const maturityDate = soon.toISOString().slice(0, 10);
		render(InvestmentCard, {
			props: { investment: makeInvestment({ maturity_date: maturityDate }) }
		});
		expect(screen.getByText(/Vence pronto/i)).toBeInTheDocument();
	});

	it('emite evento "edit" al pulsar el botón Editar', async () => {
		const { component } = render(InvestmentCard, { props: { investment: makeInvestment() } });

		let editEvent: CustomEvent | null = null;
		component.$on('edit', (e: CustomEvent) => {
			editEvent = e;
		});

		const editBtn = screen.getByText('Editar');
		await fireEvent.click(editBtn);

		expect(editEvent).not.toBeNull();
		expect((editEvent as unknown as CustomEvent).detail.investment.id).toBe('inv-1');
	});

	it('emite evento "delete" con el ID correcto tras confirmar eliminación', async () => {
		const { component } = render(InvestmentCard, { props: { investment: makeInvestment() } });

		let deleteEvent: CustomEvent | null = null;
		component.$on('delete', (e: CustomEvent) => {
			deleteEvent = e;
		});

		// Primer click activa confirmación
		const deleteBtn = screen.getByText('Eliminar');
		await fireEvent.click(deleteBtn);
		// Segundo click confirma
		const confirmBtn = screen.getByText('Sí');
		await fireEvent.click(confirmBtn);

		expect(deleteEvent).not.toBeNull();
		expect((deleteEvent as unknown as CustomEvent).detail.id).toBe('inv-1');
	});

	it('muestra skeleton de carga cuando loading=true', () => {
		render(InvestmentCard, { props: { investment: makeInvestment(), loading: true } });
		// En modo skeleton no se muestra el nombre
		expect(screen.queryByText('Depósito 2025')).toBeNull();
	});
});
