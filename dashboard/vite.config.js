import path from 'path';
import { defineConfig } from 'vite';
import proxyOptions from './proxyOptions';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
	plugins: [vue()],
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
