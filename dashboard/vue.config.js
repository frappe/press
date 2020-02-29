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
	}
};
