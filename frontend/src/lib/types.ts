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
export interface BudgetResponse {
	id: string;
	user_id: string;
	category_id: string;
	period_year: number;
	period_month: number;
	limit_amount: number;
	alert_threshold: number; // porcentaje 0-100, default 80
	name: string | null;
	created_at: string;
	updated_at: string;
}

export interface BudgetCreate {
	category_id: string;
	period_year: number;
	period_month: number;
	limit_amount: number;
	alert_threshold?: number;
	name?: string;
}

export interface BudgetUpdate {
	limit_amount?: number;
	alert_threshold?: number;
	name?: string;
}

export interface BudgetStatusResponse {
	budget: BudgetResponse;
	spent_amount: number;
	remaining_amount: number;
	percentage_used: number;
	is_over_limit: boolean;
	alert_triggered: boolean;
}

export interface BudgetAlertResponse {
	id: string;
	budget_id: string;
	triggered_at: string;
	spent_amount: number;
	percentage: number;
	is_read: boolean;
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

// ── Accounts ──────────────────────────────────────────────────────────────────
export interface AccountResponse {
	id: string;
	user_id: string;
	name: string;
	bank: string;
	account_type: 'checking' | 'savings' | 'investment' | 'credit';
	currency: string;
	balance: number;
	is_active: boolean;
	created_at: string;
	updated_at: string;
}

// ── Categories ────────────────────────────────────────────────────────────────
export interface CategoryResponse {
	id: string;
	user_id: string | null;
	parent_id: string | null;
	name: string;
	color: string | null;
	icon: string | null;
	is_system: boolean;
	created_at: string;
	updated_at: string;
}

// ── Transaction CRUD ──────────────────────────────────────────────────────────
export type TransactionType = 'income' | 'expense' | 'transfer';
export type RecurrenceRule = 'daily' | 'weekly' | 'monthly' | 'yearly';

export interface TransactionCreate {
	account_id: string;
	category_id?: string;
	amount: number;
	description: string;
	transaction_type: TransactionType;
	date: string; // YYYY-MM-DD
	is_recurring?: boolean;
	recurrence_rule?: RecurrenceRule;
	notes?: string;
}

export interface TransactionUpdate {
	category_id?: string | null;
	amount?: number;
	description?: string;
	transaction_type?: TransactionType;
	date?: string;
	is_recurring?: boolean;
	recurrence_rule?: RecurrenceRule | null;
	notes?: string;
}

export interface TransactionFilters {
	date_from?: string;
	date_to?: string;
	category_id?: string;
	account_id?: string;
	transaction_type?: TransactionType;
	page?: number;
	per_page?: number;
}

// ── CSV Import ────────────────────────────────────────────────────────────────
export type ImportRowStatus = 'imported' | 'skipped_duplicate' | 'error';

export interface ImportRowResult {
	row: number;
	status: ImportRowStatus;
	description?: string;
	amount?: number;
	date?: string;
	transaction_id?: string;
	error_detail?: string;
}

export interface ImportResult {
	account_id: string;
	dry_run: boolean;
	total_rows: number;
	imported: number;
	skipped_duplicates: number;
	errors: number;
	rows: ImportRowResult[];
}

// ── Dashboard agregado ────────────────────────────────────────────────────────
export interface DashboardData {
	overview: OverviewData;
	cashflow: CashflowMonth[];
	expensesByCategory: CategoryExpense[];
	budgetAlerts: BudgetAlertResponse[];
	recentTransactions: TransactionItem[];
}
