import path from 'path';
import { defineConfig } from 'vite';
import legacy from '@vitejs/plugin-legacy';
import proxyOptions from './proxyOptions';
import vue from '@vitejs/plugin-vue'

export default defineConfig({
	plugins: [
		legacy(),
		vue({
			template: {
				compilerOptions: {
					compatConfig: {
						MODE: 2
					}
				}
			}
		})
	],
	server: {
		port: 8080,
		proxy: proxyOptions
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
			vue: '@vue/compat'
		}
	},
	build: {
		outDir: '../press/public/dashboard',
		emptyOutDir: true,
		target: 'es2015'
	}
});
