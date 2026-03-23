const MONTH_NAMES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

const currencyFormatter = new Intl.NumberFormat('es-ES', {
	style: 'currency',
	currency: 'EUR',
	minimumFractionDigits: 2,
	maximumFractionDigits: 2
});

export function formatCurrency(amount: number): string {
	return currencyFormatter.format(amount);
}

export function formatPercent(value: number, decimals = 1): string {
	return `${value.toFixed(decimals).replace('.', ',')}%`;
}

/** Devuelve "Ene 26", "Feb 25", etc. */
export function formatMonth(year: number, month: number): string {
	const monthName = MONTH_NAMES[(month - 1) % 12];
	const shortYear = String(year).slice(-2);
	return `${monthName} ${shortYear}`;
}
