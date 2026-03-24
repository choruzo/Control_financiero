import js from '@eslint/js';
import ts from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import globals from 'globals';
import svelteParser from 'svelte-eslint-parser';

export default [
	js.configs.recommended,
	...ts.configs.recommended,
	...svelte.configs['flat/recommended'],
	{
		languageOptions: {
			globals: { ...globals.browser, ...globals.node }
		}
	},
	{
		files: ['**/*.svelte'],
		languageOptions: {
			parser: svelteParser,
			parserOptions: { parser: ts.parser }
		}
	},
	{
		ignores: ['.svelte-kit/', 'build/', 'node_modules/', 'coverage/']
	}
];
