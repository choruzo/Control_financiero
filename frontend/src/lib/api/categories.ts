import { apiFetchJson, apiFetch } from './client';
import type { CategoryResponse, CategoryCreate, CategoryUpdate } from '$lib/types';

export async function getCategories(): Promise<CategoryResponse[]> {
	return apiFetchJson<CategoryResponse[]>('/api/v1/categories');
}

export async function createCategory(data: CategoryCreate): Promise<CategoryResponse> {
	return apiFetchJson<CategoryResponse>('/api/v1/categories', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export async function updateCategory(id: string, data: CategoryUpdate): Promise<CategoryResponse> {
	return apiFetchJson<CategoryResponse>(`/api/v1/categories/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export async function deleteCategory(id: string): Promise<void> {
	const res = await apiFetch(`/api/v1/categories/${id}`, { method: 'DELETE' });
	if (!res.ok) throw new Error('Error eliminando categoría');
}
