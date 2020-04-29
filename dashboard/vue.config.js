const path = require('path');
const fs = require('fs');
const sites_path = path.resolve('../../../sites');
const common_site_config = require('../../../sites/common_site_config.json');
const { webserver_port } = common_site_config;
const sites = fs
	.readdirSync(sites_path)
	.filter(
		folder_name =>
			![
				'.build',
				'apps.txt',
				'assets',
				'common_site_config',
				'currentsite'
			].includes(folder_name)
	);

// FRAPPE_ENV will be either undefined, 'development' or 'production'
if (process.env.FRAPPE_ENV) {
	process.env.NODE_ENV = process.env.FRAPPE_ENV;
}

module.exports = {
	lintOnSave: 'warning',
	publicPath:
		process.env.NODE_ENV === 'production' ? '/assets/press/dashboard/' : '/',
	outputDir: path.resolve('../press/public/dashboard'),
	indexPath: path.resolve('../press/www/dashboard.html'),
	devServer: {
		allowedHosts: sites,
		proxy: {
			'^/api': {
				target: `http://localhost:${webserver_port}`,
				ws: true,
				changeOrigin: true,
				router: function(req) {
					const site_name = req.headers.host.split(':')[0];
					return `http://${site_name}:${webserver_port}`;
				}
			}
		}
	},
	pwa: {
		iconPaths: {
			favicon32: 'img/icons/favicon.png',
			favicon16: 'img/icons/favicon.png',
			appleTouchIcon: 'img/icons/favicon.png',
			maskIcon: 'img/icons/favicon.png',
			msTileImage: 'img/icons/favicon.png'
		}
	}
};
