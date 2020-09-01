let config = require('dashboard/tailwind.config');
module.exports = {
	theme: config.theme,
	plugins: [require('@tailwindcss/ui')],
	purge: {
		content: ['./src/**/*.html', './src/**/*.vue'],
		options: {
			whitelist: [
				'body',
				'html',
				'img',
				'a',
				'g-image',
				'g-image--lazy',
				'g-image--loaded'
			],
			whitelistPatternsChildren: [/chart-container$/, /graph-svg-tip$/]
		}
	}
};
