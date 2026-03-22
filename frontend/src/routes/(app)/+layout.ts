import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async ({ url }) => {
	if (!browser) return {};

	const token = localStorage.getItem('fc_access_token');
	if (!token) {
		// Preservar la URL de destino para redirigir después del login
		const redirectTo = url.pathname !== '/' ? url.pathname : '/dashboard';
		throw redirect(302, `/login?redirect=${encodeURIComponent(redirectTo)}`);
	}

	return {};
};
