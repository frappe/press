import baseConfig from './vite.config';

export default {
	...baseConfig,
	plugins: [
		...(baseConfig as any).plugins,
		{
			name: 'preview-port',
			config: () => ({ server: { port: 8085, strictPort: true } }),
		},
	],
};
