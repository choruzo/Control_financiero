import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import BudgetCard from '$lib/components/budgets/BudgetCard.svelte';
import type { BudgetStatusResponse } from '$lib/types';

function makeStatus(overrides: Partial<BudgetStatusResponse> = {}): BudgetStatusResponse {
	return {
		budget: {
			id: 'bud-1',
			user_id: 'user-1',
			category_id: 'cat-1',
			period_year: 2026,
			period_month: 3,
			limit_amount: 500,
			alert_threshold: 80,
			name: null,
			created_at: '',
			updated_at: ''
		},
		spent_amount: 200,
		remaining_amount: 300,
		percentage_used: 40,
		is_over_limit: false,
		alert_triggered: false,
		...overrides
	};
}

describe('BudgetCard', () => {
	it('muestra el nombre de la categoría cuando el presupuesto no tiene nombre', () => {
		render(BudgetCard, {
			props: { status: makeStatus(), categoryName: 'Alimentación' }
		});
		expect(screen.getByText('Alimentación')).toBeInTheDocument();
	});

	it('muestra el nombre del presupuesto cuando está definido', () => {
		const status = makeStatus();
		status.budget.name = 'Mi presupuesto comida';
		render(BudgetCard, { props: { status, categoryName: 'Alimentación' } });
		expect(screen.getByText('Mi presupuesto comida')).toBeInTheDocument();
	});

	it('muestra el porcentaje de uso en el texto', () => {
		render(BudgetCard, {
			props: { status: makeStatus({ percentage_used: 40 }), categoryName: 'Transporte' }
		});
		expect(screen.getByText('40.0%')).toBeInTheDocument();
	});

	it('muestra badge "Superado" cuando is_over_limit es true', () => {
		const status = makeStatus({
			spent_amount: 600,
			remaining_amount: -100,
			percentage_used: 120,
			is_over_limit: true,
			alert_triggered: true
		});
		render(BudgetCard, { props: { status, categoryName: 'Ocio' } });
		expect(screen.getByText(/Superado/i)).toBeInTheDocument();
	});

	it('muestra badge "Alerta" cuando alert_triggered es true pero no is_over_limit', () => {
		const status = makeStatus({
			spent_amount: 420,
			remaining_amount: 80,
			percentage_used: 84,
			is_over_limit: false,
			alert_triggered: true
		});
		render(BudgetCard, { props: { status, categoryName: 'Hogar' } });
		expect(screen.getByText(/Alerta/i)).toBeInTheDocument();
		expect(screen.queryByText(/Superado/i)).toBeNull();
	});

	it('no muestra ningún badge cuando el gasto está dentro del umbral', () => {
		render(BudgetCard, {
			props: {
				status: makeStatus({ percentage_used: 40, is_over_limit: false, alert_triggered: false }),
				categoryName: 'Salud'
			}
		});
		expect(screen.queryByText(/Superado/i)).toBeNull();
		expect(screen.queryByText(/Alerta/i)).toBeNull();
	});

	it('emite evento "edit" al pulsar el botón Editar', async () => {
		const { component } = render(BudgetCard, {
			props: { status: makeStatus(), categoryName: 'Alimentación' }
		});

		let editEvent: CustomEvent | null = null;
		component.$on('edit', (e: CustomEvent) => {
			editEvent = e;
		});

		const editBtn = screen.getByText('Editar');
		await fireEvent.click(editBtn);

		expect(editEvent).not.toBeNull();
		expect((editEvent as unknown as CustomEvent).detail.budget.id).toBe('bud-1');
	});
});
