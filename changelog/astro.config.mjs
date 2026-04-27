// @ts-check
import { defineConfig } from 'astro/config';
import { urlToVidTag } from './src/utils';

import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	site: 'https://cloud.frappe.io',
	base: '/changelog',

	markdown: {
		remarkPlugins: [urlToVidTag],
	},

	vite: {
		plugins: [tailwindcss()],
	},

	outDir: '../press/www/changelog',
});
