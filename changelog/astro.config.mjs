// @ts-check
import { defineConfig } from 'astro/config';
import { urlToVidTag, rehypeFirstH1Link } from './src/utils';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	site: 'https://cloud.frappe.io',
	base: '/releases',

	markdown: {
		remarkPlugins: [urlToVidTag],
		rehypePlugins: [rehypeFirstH1Link],
	},

	vite: {
		plugins: [tailwindcss()],
	},

	outDir: '../press/www/releases',

	image: {
		domains: ['github.com'],
		remotePatterns: [
			{ hostname: '**.github.com' },
			{ hostname: '**.githubusercontent.com' },
		],
	},
});
