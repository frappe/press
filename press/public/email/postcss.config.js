const path = require('path');
const purgecss = require('@fullhuman/postcss-purgecss')({
	content: ['./press/templates/emails/*.html'],
	defaultExtractor: content => content.match(/[\w-/:]+(?<!:)/g) || []
});
const tailwindcss = require('tailwindcss');
const config_path = path.resolve(__dirname, './tailwind.config.js');

module.exports = {
	plugins: [tailwindcss(config_path), purgecss]
};
