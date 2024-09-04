import path from 'path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import vueJsx from '@vitejs/plugin-vue-jsx';
import frappeui from 'frappe-ui/vite';
import pluginRewriteAll from 'vite-plugin-rewrite-all';
import Components from 'unplugin-vue-components/vite';
import Icons from 'unplugin-icons/vite';
import IconsResolver from 'unplugin-icons/resolver';
import { sentryVitePlugin } from '@sentry/vite-plugin';

export default defineConfig({
	plugins: [
		vue(),
		vueJsx(),
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
		Icons(),
		sentryVitePlugin({
			url: process.env.SENTRY_URL,
			org: process.env.SENTRY_ORG,
			project: process.env.SENTRY_PROJECT,
			applicationKey: 'press-dashboard',
			authToken: process.env.SENTRY_AUTH_TOKEN
		})
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
				main: path.resolve(__dirname, 'index.html')
			}
		}
	},
	// @ts-ignore
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
