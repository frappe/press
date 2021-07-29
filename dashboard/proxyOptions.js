const common_site_config = require('../../../sites/common_site_config.json');
let { webserver_port } = common_site_config;

// webserver_port = 8009

module.exports = {
	'^/(app|api|assets|files)': {
		target: `http://localhost:${webserver_port}`,
		ws: true,
		router: function(req) {
			const site_name = req.headers.host.split(':')[0];
			return `http://${site_name}:${webserver_port}`;
		}
	}
};
