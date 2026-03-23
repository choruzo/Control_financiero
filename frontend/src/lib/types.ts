// Auth
export interface Token {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

export interface User {
	id: string; // UUID como string
	email: string;
	is_active: boolean;
	created_at: string; // ISO 8601
}

export interface UserCreate {
	email: string;
	password: string;
}

// Estado de autenticación para el store
export interface AuthState {
	user: User | null;
	accessToken: string | null;
	refreshToken: string | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

// Respuesta de error de la API
export interface ApiErrorResponse {
	detail: string | ValidationError[];
}

export interface ValidationError {
	loc: (string | number)[];
	msg: string;
	type: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export interface OverviewData {
	year: number;
	month: number;
	total_income: number;
	total_expenses: number;
	net_savings: number;
	savings_rate: number;
	total_balance: number;
	transaction_count: number;
}

export interface CashflowMonth {
	year: number;
	month: number;
	total_income: number;
	total_expenses: number;
	net: number;
}

export interface CategoryExpense {
	category_id: string | null;
	category_name: string;
	total_amount: number;
	transaction_count: number;
	percentage: number;
}

export interface SavingsRateMonth {
	year: number;
	month: number;
	income: number;
	expenses: number;
	net_savings: number;
	savings_rate: number;
	moving_avg_3m: number | null;
	moving_avg_6m: number | null;
}

// ── Budgets ───────────────────────────────────────────────────────────────────
export interface BudgetAlertResponse {
	id: string;
	budget_id: string;
	triggered_at: string;
	spent_amount: number;
	percentage: number;
	is_read: boolean;
}

export interface BudgetDetail {
	id: string;
	category_id: string | null;
	limit_amount: number;
	alert_threshold: number;
	period_year: number;
	period_month: number;
}

export interface BudgetStatusItem {
	budget: BudgetDetail;
	spent_amount: number;
	remaining_amount: number;
	percentage_used: number;
	is_over_limit: boolean;
	alert_triggered: boolean;
}

// ── Transactions ──────────────────────────────────────────────────────────────
export interface TransactionItem {
	id: string;
	account_id: string;
	amount: number;
	description: string;
	transaction_type: 'income' | 'expense' | 'transfer';
	date: string;
	category_id: string | null;
	is_recurring: boolean;
	ml_suggested_category_id: string | null;
	ml_confidence: number | null;
}

export interface PaginatedTransactions {
	items: TransactionItem[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

// ── Dashboard agregado ────────────────────────────────────────────────────────
export interface DashboardData {
	overview: OverviewData;
	cashflow: CashflowMonth[];
	expensesByCategory: CategoryExpense[];
	budgetAlerts: BudgetAlertResponse[];
	recentTransactions: TransactionItem[];
}
