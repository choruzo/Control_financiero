import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: '0.0.0.0',
		port: 3000,
		proxy: {
			// Para fetch SSR dentro del contenedor Docker
			'/api': {
				target: 'http://backend:8000',
				changeOrigin: true
			}
		}
	},
	test: {
		globals: true,
		environment: 'jsdom',
		setupFiles: ['./tests/setup.ts'],
		include: ['tests/**/*.test.ts'],
		coverage: {
			provider: 'v8',
			reporter: ['text', 'html'],
			include: ['src/**/*.ts', 'src/**/*.svelte']
		}
	}
});
