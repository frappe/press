import path from 'path';
import { defineConfig } from 'vite';
import { createVuePlugin } from 'vite-plugin-vue2';
import legacy from '@vitejs/plugin-legacy';
import proxyOptions from './proxyOptions';

export default defineConfig({
	plugins: [createVuePlugin(), legacy()],
	server: {
		port: 8080,
		proxy: proxyOptions
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src')
		}
	},
	build: {
		outDir: '../press/public/dashboard',
		emptyOutDir: true,
		target: 'es2015'
	}
});
