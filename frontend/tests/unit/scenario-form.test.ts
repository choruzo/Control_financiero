import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import ScenarioForm from '$lib/components/predictions/ScenarioForm.svelte';

describe('ScenarioForm', () => {
	it('renderiza con valores por defecto correctos', () => {
		const { getByLabelText } = render(ScenarioForm, { props: { loading: false } });

		const monthsSlider = getByLabelText(/meses a simular/i) as HTMLInputElement;
		expect(monthsSlider.value).toBe('6');

		const salarySlider = getByLabelText(/variación de sueldo/i) as HTMLInputElement;
		expect(salarySlider.value).toBe('0');
	});

	it('muestra spinner y deshabilita el botón cuando loading=true', () => {
		const { getByRole } = render(ScenarioForm, { props: { loading: true } });
		const btn = getByRole('button', { name: /analizando/i });
		expect(btn).toBeDisabled();
	});

	it('el botón está habilitado cuando loading=false', () => {
		const { getByRole } = render(ScenarioForm, { props: { loading: false } });
		const btn = getByRole('button', { name: /analizar escenario/i });
		expect(btn).not.toBeDisabled();
	});

	it('botón "Añadir" agrega un gasto recurrente', async () => {
		const { getByRole, getAllByPlaceholderText } = render(ScenarioForm, {
			props: { loading: false }
		});

		const addBtn = getByRole('button', { name: /añadir/i });
		await fireEvent.click(addBtn);

		const descInputs = getAllByPlaceholderText(/descripción/i);
		expect(descInputs).toHaveLength(1);
	});

	it('botón X elimina un gasto recurrente', async () => {
		const { getByRole, getAllByPlaceholderText, getAllByLabelText } = render(ScenarioForm, {
			props: { loading: false }
		});

		const addBtn = getByRole('button', { name: /añadir/i });
		await fireEvent.click(addBtn);
		await fireEvent.click(addBtn);

		expect(getAllByPlaceholderText(/descripción/i)).toHaveLength(2);

		const removeButtons = getAllByLabelText(/eliminar gasto/i);
		await fireEvent.click(removeButtons[0]);

		expect(getAllByPlaceholderText(/descripción/i)).toHaveLength(1);
	});

	it('emite evento submit con los valores del formulario', async () => {
		const { getByRole, component } = render(ScenarioForm, { props: { loading: false } });

		const submitEvents: CustomEvent[] = [];
		component.$on('submit', (e: CustomEvent) => submitEvents.push(e));

		const btn = getByRole('button', { name: /analizar escenario/i });
		await fireEvent.click(btn);

		expect(submitEvents).toHaveLength(1);
		const detail = submitEvents[0].detail;
		expect(detail).toMatchObject({ months_ahead: 6, monte_carlo_simulations: 1000 });
		// salary_variation_pct=0 → undefined en el request
		expect(detail.salary_variation_pct).toBeUndefined();
	});

	it('emite variación de sueldo solo si es distinta de 0', async () => {
		const { getByLabelText, getByRole, component } = render(ScenarioForm, {
			props: { loading: false }
		});

		const submitEvents: CustomEvent[] = [];
		component.$on('submit', (e: CustomEvent) => submitEvents.push(e));

		const slider = getByLabelText(/variación de sueldo/i) as HTMLInputElement;
		await fireEvent.input(slider, { target: { value: '15' } });

		const btn = getByRole('button', { name: /analizar escenario/i });
		await fireEvent.click(btn);

		const detail = submitEvents[0].detail;
		expect(detail.salary_variation_pct).toBe(15);
	});
});
