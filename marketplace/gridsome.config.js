// This is where project configuration and plugin options are located.
// Learn more: https://gridsome.org/docs/config

// Changes here require a server restart.
// To restart press CTRL + C in terminal and run `gridsome develop`
const path = require('path');

module.exports = {
	siteName: 'Frappe Cloud',
	plugins: [],
	css: {
		loaderOptions: {
			postcss: {
				plugins: [require('tailwindcss'), require('autoprefixer')],
			},
		},
	},
};
