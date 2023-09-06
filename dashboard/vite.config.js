import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import frappeui from 'frappe-ui/vite';
import pluginRewriteAll from 'vite-plugin-rewrite-all';

export default defineConfig({
	plugins: [vue(), pluginRewriteAll(), frappeui()],
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src')
		}
	},
	optimizeDeps: {
		include: ['feather-icons', 'showdown']
	},
	build: {
		outDir: '../press/public/dashboard',
		emptyOutDir: true,
		sourcemap: true,
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
