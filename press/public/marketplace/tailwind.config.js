const config = require('../../../dashboard/tailwind.config');

module.exports = {
	theme: config.theme,
	plugins: config.plugins,
	content: [
		'./press/**/marketplace/**/*.html',
		'./press/**/marketplace_*.html',
	],
};
