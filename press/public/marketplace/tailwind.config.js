const config = require('../../../dashboard/tailwind.config');

module.exports = {
	theme: config.theme,
	plugins: config.plugins,
	purge: {
		content: [
			'./press/**/marketplace/**/*.html',
			'./press/**/marketplace_*.html',
		],
		options: {
			whitelist: ['body', 'html', 'img', 'a'],
			whitelistPatternsChildren: [/chart-container$/, /graph-svg-tip$/],
		},
	},
};
