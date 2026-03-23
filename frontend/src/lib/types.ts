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
export type AccountType = 'checking' | 'savings' | 'investment' | 'credit';

export interface AccountCreate {
	name: string;
	bank: string;
	account_type: AccountType;
	currency?: string;
	balance: number;
}

export interface AccountUpdate {
	name?: string;
	bank?: string;
	account_type?: AccountType;
	currency?: string;
	balance?: number;
	is_active?: boolean;
}

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

// ── Investments ───────────────────────────────────────────────────────────────
export type InvestmentType = 'deposit' | 'fund' | 'stock' | 'bond';
export type InterestType = 'simple' | 'compound';
export type CompoundingFrequency = 'annually' | 'quarterly' | 'monthly';

export interface InvestmentResponse {
	id: string;
	user_id: string;
	account_id: string | null;
	name: string;
	investment_type: InvestmentType;
	principal_amount: number;
	interest_rate: number;
	interest_type: InterestType;
	compounding_frequency: CompoundingFrequency | null;
	current_value: number | null;
	start_date: string; // YYYY-MM-DD
	maturity_date: string | null;
	auto_renew: boolean;
	renewal_period_months: number | null;
	renewals_count: number;
	notes: string | null;
	is_active: boolean;
	created_at: string;
	updated_at: string;
}

export interface InvestmentCreate {
	name: string;
	investment_type: InvestmentType;
	principal_amount: number;
	interest_rate: number;
	interest_type: InterestType;
	start_date: string;
	compounding_frequency?: CompoundingFrequency;
	maturity_date?: string;
	auto_renew?: boolean;
	renewal_period_months?: number;
	current_value?: number;
	account_id?: string;
	notes?: string;
}

export interface InvestmentUpdate {
	name?: string;
	interest_rate?: number;
	maturity_date?: string;
	auto_renew?: boolean;
	renewal_period_months?: number;
	current_value?: number;
	notes?: string;
	is_active?: boolean;
}

export interface InvestmentStatusResponse {
	investment: InvestmentResponse;
	accrued_interest: number;
	total_return: number;
	return_percentage: number;
	days_held: number;
	days_to_maturity: number | null;
}

export interface InvestmentSummaryResponse {
	total_investments: number;
	total_principal: number;
	total_current_value: number;
	total_return: number;
	average_return_percentage: number;
	by_type: Record<string, number>;
}

// ── Mortgage ─────────────────────────────────────────────────────────────────
export type MortgageRateType = 'fixed' | 'variable' | 'mixed';
export type MortgagePropertyType = 'new' | 'second_hand';
export type MortgageReviewFrequency = 'annual' | 'semiannual';

export interface AmortizationRow {
	month: number;
	payment: number;
	principal: number;
	interest: number;
	balance: number;
	applied_rate: number;
}

export interface ClosingCosts {
	notary: number;
	registry: number;
	tax: number;
	gestor: number;
	appraisal: number;
	total: number;
}

export interface MortgageSimulateRequest {
	property_price: number;
	down_payment: number;
	rate_type: MortgageRateType;
	term_years: number;
	interest_rate?: number;
	euribor_rate?: number;
	spread?: number;
	fixed_years?: number;
	review_frequency?: MortgageReviewFrequency;
	include_costs?: boolean;
	property_type?: MortgagePropertyType;
	region_tax_rate?: number;
}

export interface MortgageSimulationResult {
	loan_amount: number;
	rate_type: string;
	term_years: number;
	initial_monthly_payment: number;
	total_amount_paid: number;
	total_interest: number;
	effective_annual_rate: number;
	schedule: AmortizationRow[];
	closing_costs: ClosingCosts | null;
}

export interface ScenarioParams {
	name: string;
	rate_type: MortgageRateType;
	interest_rate?: number;
	euribor_rate?: number;
	spread?: number;
	fixed_years?: number;
	review_frequency?: MortgageReviewFrequency;
}

export interface MortgageCompareRequest {
	property_price: number;
	down_payment: number;
	term_years: number;
	scenarios: ScenarioParams[];
}

export interface MortgageScenarioSummary {
	name: string;
	rate_type: string;
	initial_monthly_payment: number;
	total_amount_paid: number;
	total_interest: number;
	savings_vs_first: number | null;
}

export interface MortgageCompareResponse {
	loan_amount: number;
	term_years: number;
	scenarios: MortgageScenarioSummary[];
}

export interface MaxLoanOption {
	description: string;
	rate_type: string;
	interest_rate: number;
	term_years: number;
	max_loan: number;
	monthly_payment: number;
}

export interface AffordabilityResponse {
	monthly_net_income: number;
	max_monthly_payment: number;
	recommended_max_loan: number;
	options: MaxLoanOption[];
}

export interface MortgageSaveRequest extends MortgageSimulateRequest {
	name: string;
}

export interface MortgageSimulationResponse {
	id: string;
	name: string;
	property_price: number;
	down_payment: number;
	loan_amount: number;
	rate_type: string;
	term_years: number;
	interest_rate: number | null;
	euribor_rate: number | null;
	spread: number | null;
	fixed_years: number | null;
	review_frequency: string | null;
	property_type: string;
	region_tax_rate: number | null;
	initial_monthly_payment: number;
	total_amount_paid: number;
	total_interest: number;
	created_at: string;
}

export interface StressTestResult {
	euribor_rate: number;
	euribor_label: string;
	max_loan_p10: number;
	max_loan_p50: number;
	max_loan_p90: number;
	monthly_payment_p50: number;
	is_affordable: boolean;
}

export interface AIAffordabilityResponse {
	forecast_monthly_income_p10: number;
	forecast_monthly_income_p50: number;
	forecast_monthly_income_p90: number;
	forecast_max_monthly_payment: number;
	forecast_recommended_max_loan: number;
	current_based: AffordabilityResponse;
	stress_tests: StressTestResult[];
	ml_available: boolean;
	historical_months_used: number;
	months_ahead_used: number;
	model_used: string;
}

// ── Predictions & Scenarios ───────────────────────────────────────────────────
export interface ForecastMonth {
	year: number;
	month: number;
	income_p10: number;
	income_p50: number;
	income_p90: number;
	expenses_p10: number;
	expenses_p50: number;
	expenses_p90: number;
	net_p10: number;
	net_p50: number;
	net_p90: number;
}

export interface CashflowForecast {
	predictions: ForecastMonth[];
	model_used: string;
	model_version: string;
	historical_months_used: number;
	ml_available: boolean;
}

export interface RecurringExpenseModification {
	description: string;
	monthly_amount: number;
	action: 'add' | 'remove';
}

export interface ScenarioRequest {
	name?: string;
	months_ahead?: number;
	salary_variation_pct?: number;
	euribor_variation_pct?: number;
	recurring_expense_modifications?: RecurringExpenseModification[];
	gross_annual?: number;
	tax_year?: number;
	monte_carlo_simulations?: number;
}

export interface ScenarioMonthResult {
	year: number;
	month: number;
	base_income: number;
	base_expenses: number;
	base_net: number;
	scenario_income: number;
	scenario_expenses: number;
	scenario_net_p10: number;
	scenario_net_p50: number;
	scenario_net_p90: number;
	tax_monthly_base: number | null;
	tax_monthly_scenario: number | null;
	tax_monthly_delta: number | null;
}

export interface ScenarioSummary {
	period_months: number;
	total_base_net: number;
	total_scenario_net_p50: number;
	total_net_improvement: number;
	total_net_improvement_p10: number;
	total_net_improvement_p90: number;
	avg_monthly_improvement: number;
	net_improvement_pct: number | null;
	total_tax_impact: number | null;
}

export interface ScenarioResponse {
	name: string;
	parameters: ScenarioRequest;
	monthly_results: ScenarioMonthResult[];
	summary: ScenarioSummary;
	mortgage_impact_per_month: number | null;
	historical_months_used: number;
	ml_available: boolean;
}

export interface MLModelStatus {
	loaded: boolean;
	version: string | null;
	accuracy: number | null;
	last_trained: string | null;
	feedback_count: number;
	retrain_in_progress: boolean;
	ml_available: boolean;
}

// ── Category CRUD ─────────────────────────────────────────────────────────────
export interface CategoryCreate {
	name: string;
	parent_id?: string;
	color?: string;
	icon?: string;
}

export interface CategoryUpdate {
	name?: string;
	parent_id?: string;
	color?: string;
	icon?: string;
}

// ── Tax ───────────────────────────────────────────────────────────────────────
export interface TaxBracketResponse {
	id: string;
	tax_year: number;
	bracket_type: 'general' | 'savings';
	min_amount: number;
	max_amount: number | null;
	rate: number;
}

export interface TaxConfigCreate {
	tax_year: number;
	gross_annual_salary: number;
}

export interface TaxConfigUpdate {
	gross_annual_salary: number;
}

export interface TaxConfigResponse {
	id: string;
	tax_year: number;
	gross_annual_salary: number;
	created_at: string;
	updated_at: string;
}

export interface BracketBreakdown {
	rate: number;
	taxable_in_bracket: number;
	tax_in_bracket: number;
}

export interface TaxCalculationResponse {
	tax_year: number;
	gross_annual: number;
	ss_annual: number;
	ss_rate: number;
	work_expenses_deduction: number;
	taxable_base: number;
	irpf_annual: number;
	effective_rate: number;
	net_annual: number;
	net_monthly: number;
	bracket_breakdown: BracketBreakdown[];
}

// ── Dashboard agregado ────────────────────────────────────────────────────────
export interface DashboardData {
	overview: OverviewData;
	cashflow: CashflowMonth[];
	expensesByCategory: CategoryExpense[];
	budgetAlerts: BudgetAlertResponse[];
	recentTransactions: TransactionItem[];
}
