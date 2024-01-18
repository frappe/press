import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import frappeui from 'frappe-ui/vite';
import pluginRewriteAll from 'vite-plugin-rewrite-all';
import Components from 'unplugin-vue-components/vite';
import Icons from 'unplugin-icons/vite';
import IconsResolver from 'unplugin-icons/resolver';

export default defineConfig({
	plugins: [
		vue(),
		pluginRewriteAll(),
		frappeui(),
		Components({
			dirs: [
				'src/components',
				// 'src2/components',
				'node_modules/frappe-ui/src/components'
			],
			resolvers: [IconsResolver()]
		}),
		Icons()
	],
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
		target: 'es2015',
		rollupOptions: {
			input: {
				main: path.resolve(__dirname, 'index.html'),
				dashboard2: path.resolve(__dirname, 'dashboard2.html')
			}
		}
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
