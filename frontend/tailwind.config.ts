import { join } from 'path';
import type { Config } from 'tailwindcss';
import { skeleton } from '@skeletonlabs/tw-plugin';

const config: Config = {
	// Modo oscuro basado en clase: Skeleton gestiona la clase 'dark' en <html>
	darkMode: 'class',
	content: [
		'./src/**/*.{html,js,svelte,ts}',
		// CRÍTICO: incluir componentes de Skeleton para evitar purge de clases
		join(require.resolve('@skeletonlabs/skeleton'), '../**/*.{html,js,svelte,ts}')
	],
	theme: {
		extend: {}
	},
	plugins: [
		skeleton({
			themes: {
				preset: [
					{
						name: 'wintry',
						enhancements: true
					}
				]
			}
		})
	]
};

export default config;
