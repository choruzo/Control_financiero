import { apiFetchJson } from './client';
import type { CategoryResponse } from '$lib/types';

export async function getCategories(): Promise<CategoryResponse[]> {
	return apiFetchJson<CategoryResponse[]>('/api/v1/categories');
}
