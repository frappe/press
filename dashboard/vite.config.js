import path from 'path';
import { defineConfig } from 'vite';
import proxyOptions from './proxyOptions';
import vue from '@vitejs/plugin-vue';
import pluginRewriteAll from 'vite-plugin-rewrite-all';

export default defineConfig({
	plugins: [vue(), pluginRewriteAll()],
	server: {
		port: 8080,
		proxy: proxyOptions
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src')
		}
	},
	optimizeDeps: {
		include: ['feather-icons']
	},
	build: {
		outDir: '../press/public/dashboard',
		emptyOutDir: true,
		target: 'es2015'
	},
	test: {
		globals: true,
		environment: 'jsdom',
		setupFiles: 'src/tests/setup/msw.js',
		coverage: {
			extension: ['.vue', '.js'],
			all: true
		}
	}
});
