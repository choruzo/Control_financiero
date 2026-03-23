import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import KpiCard from '$lib/components/dashboard/KpiCard.svelte';

describe('KpiCard', () => {
	it('renderiza el label correctamente', () => {
		render(KpiCard, { props: { label: 'Balance total', value: 1000 } });
		expect(screen.getByText('Balance total')).toBeInTheDocument();
	});

	it('formatea el valor como moneda por defecto', () => {
		render(KpiCard, { props: { label: 'Balance', value: 1234.56 } });
		// El entorno JSDOM puede no tener ICU completa; comprobamos dígitos y símbolo €
		const valueEl = screen.getByText(/1[.,]?234[.,]56/);
		expect(valueEl).toBeInTheDocument();
		expect(valueEl.textContent).toContain('€');
	});

	it('formatAs=percent muestra el valor como porcentaje', () => {
		render(KpiCard, { props: { label: 'Ahorro', value: 25.5, formatAs: 'percent' } });
		expect(screen.getByText('25,5%')).toBeInTheDocument();
	});

	it('value=null muestra el guion largo', () => {
		render(KpiCard, { props: { label: 'Sin datos', value: null } });
		expect(screen.getByText('—')).toBeInTheDocument();
	});

	it('loading=true muestra el skeleton y no el valor', () => {
		const { container } = render(KpiCard, { props: { label: 'Balance', value: 9999, loading: true } });
		// El skeleton usa animate-pulse
		expect(container.querySelector('.animate-pulse')).not.toBeNull();
		// El valor no debe aparecer mientras carga
		expect(screen.queryByText(/9\.999/)).toBeNull();
	});

	it('trend positivo muestra clase text-success-400', () => {
		const { container } = render(KpiCard, { props: { label: 'Ingresos', value: 2000, trend: 5.3 } });
		const trendEl = container.querySelector('.text-success-400');
		expect(trendEl).not.toBeNull();
		expect(trendEl?.textContent).toContain('+5.3%');
	});
});
