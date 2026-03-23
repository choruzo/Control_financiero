import { describe, it, expect } from 'vitest';
import { formatCurrency, formatPercent, formatMonth } from '$lib/utils/format';

describe('format utils', () => {
	describe('formatCurrency', () => {
		it('formatea un entero con símbolo €', () => {
			expect(formatCurrency(1000)).toContain('€');
			expect(formatCurrency(1000)).toContain('1');
		});

		it('formatea con dos decimales', () => {
			const result = formatCurrency(1234.56);
			// El entorno de test puede no tener ICU completa; verificamos partes invariantes
			expect(result).toContain('€');
			expect(result).toMatch(/1[.,]?234[.,]56/);
		});

		it('formatea cero correctamente', () => {
			expect(formatCurrency(0)).toContain('0,00');
		});
	});

	describe('formatPercent', () => {
		it('formatea con coma decimal', () => {
			expect(formatPercent(25.5)).toBe('25,5%');
		});

		it('admite decimals=0', () => {
			expect(formatPercent(33.3, 0)).toBe('33%');
		});

		it('formatea el 100%', () => {
			expect(formatPercent(100)).toBe('100,0%');
		});
	});

	describe('formatMonth', () => {
		it('devuelve la abreviatura correcta para enero', () => {
			expect(formatMonth(2026, 1)).toBe('Ene 26');
		});

		it('devuelve la abreviatura correcta para diciembre', () => {
			expect(formatMonth(2025, 12)).toBe('Dic 25');
		});

		it('usa los dos últimos dígitos del año', () => {
			expect(formatMonth(2030, 6)).toBe('Jun 30');
		});
	});
});
