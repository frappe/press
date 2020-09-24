const path = require('path');
const tailwindcss = require('tailwindcss');
const config_path = path.resolve(__dirname, './tailwind.config.js');

module.exports = {
	plugins: [require('autoprefixer'), tailwindcss(config_path)]
};
