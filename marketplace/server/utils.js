const fetch = require('node-fetch');
const common_site_config = require('../../../../sites/common_site_config.json');
const {
	marketplace_api_user,
	marketplace_api_password,
	marketplace_url
} = common_site_config;

let sid = null;

async function getMarketplaceApps() {
	if (!sid) {
		await call('login', {
			usr: marketplace_api_user,
			pwd: marketplace_api_password
		});
	}
	return call('press.api.app.marketplace_apps');
}

async function call(method, args) {
	let headers = {
		Accept: 'application/json',
		'Content-Type': 'application/json; charset=utf-8'
	};
	// prettier-ignore
	let url = `${marketplace_url}/api/method/${method}${sid ? `?sid=${sid}` : ''}`;
	const res = await fetch(url, {
		method: 'POST',
		headers,
		body: JSON.stringify(args)
	});

	let cookies = res.headers.raw()['set-cookie'];
	for (let cookie in cookies) {
		if (cookie.includes('sid=')) {
			let map = Object.fromEntries(
				cookie.split('; ').map(part => part.split('='))
			);
			sid = map.sid;
			break;
		}
	}

	if (res.ok) {
		const data = await res.json();
		if (data.docs || method === 'login') {
			return data;
		}
		return data.message;
	} else {
		let response = await res.text();
		let error, exception;
		try {
			error = JSON.parse(response);
			// eslint-disable-next-line no-empty
		} catch (e) {}
		let errorParts = [
			[method, error.exc_type, error._error_message]
				.filter(Boolean)
				.join(' ')
		];

		if (error.exc) {
			exception = error.exc;
			try {
				exception = JSON.parse(exception)[0];
				// eslint-disable-next-line no-empty
			} catch (e) {}
			errorParts.push(exception);
		}
		let e = new Error(errorParts.join('\n'));
		e.exc_type = error.exc_type;
		e.exc = exception;
		e.messages = error._server_messages
			? JSON.parse(error._server_messages)
			: [];
		e.messages = e.messages.concat(error.message);
		e.messages = e.messages.map(m => {
			try {
				return JSON.parse(m).message;
			} catch (error) {
				return m;
			}
		});
		e.messages = e.messages.filter(Boolean);
		if (!e.messages.length) {
			e.messages = ['Internal Server Error'];
		}
		throw e;
	}
}

module.exports = {
	call,
	getMarketplaceApps
};
