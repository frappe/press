const config = require('../../../dashboard/tailwind.config');

module.exports = {
	presets: config.presets,
	theme: config.theme,
	plugins: config.plugins,
	content: [
		'./press/**/marketplace/**/*.html',
		'./press/**/marketplace/*.html',
		'./press/**/marketplace_*.html',
	],
};
