const config = require('../../../dashboard/tailwind.config');

module.exports = {
	theme: config.theme,
	plugins: config.plugins,
	content: ['./press/**/saas/*.html', './press/**/saas/*.html'],
};
