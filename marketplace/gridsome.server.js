// Server API makes it possible to hook into various parts of Gridsome
// on server-side and add custom data to the GraphQL data layer.
// Learn more: https://gridsome.org/docs/server-api/

// Changes here require a server restart.
// To restart press CTRL + C in terminal and run `gridsome develop`

const path = require('path');
const fs = require('fs');
const sites_path = path.resolve('../../../sites');
const common_site_config = require('../../../sites/common_site_config.json');
const {
	webserver_port,
	marketplace_api_user,
	marketplace_api_password
} = common_site_config;
const { createProxyMiddleware } = require('http-proxy-middleware');
const { getMarketplaceApps } = require('./server/utils');
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

module.exports = function(api) {
	api.loadSource(async ({ addCollection }) => {
		// Use the Data Store API here: https://gridsome.org/docs/data-store-api/

		let apps = await getMarketplaceApps();
		console.log(`\nAdding ${apps.length} marketplace apps to collection\n`);

		let appsCollection = addCollection({
			typeName: 'FrappeApps'
		});

		for (let app of apps) {
			appsCollection.addNode({
				id: app.name,
				...app
			});
		}
	});

	api.createPages(({ createPage }) => {
		// Use the Pages API here: https://gridsome.org/docs/pages-api/
	});

	api.configureServer(app => {
		const options = {
			'^/api': {
				target: `http://localhost:${webserver_port}`,
				ws: true,
				changeOrigin: true,
				router: function(req) {
					const site_name = req.headers.host.split(':')[0];
					return `http://${site_name}:${webserver_port}`;
				}
			}
		};
		for (let option in options) {
			let route = option;
			let routeOptions = options[route];
			const proxy = createProxyMiddleware(routeOptions);
			app.use(route, proxy);
		}
	});
};
