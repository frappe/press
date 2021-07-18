import router from '@/router';

export default async function call(method, args) {
	if (!args) {
		args = {};
	}

	let headers = {
		Accept: 'application/json',
		'Content-Type': 'application/json; charset=utf-8',
		'X-Frappe-Site-Name': window.location.hostname
	};

	let team = localStorage.getItem('current_team') || null;
	if (team) {
		headers['X-Press-Team'] = team;
	}

	if (window.csrf_token && window.csrf_token !== '{{ csrf_token }}') {
		headers['X-Frappe-CSRF-Token'] = window.csrf_token;
	}

	updateState(this, 'RequestStarted', null);

	const res = await fetch(`/api/method/${method}`, {
		method: 'POST',
		headers,
		body: JSON.stringify(args)
	});

	if (res.ok) {
		updateState(this, null, null);
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
			[method, error.exc_type, error._error_message].filter(Boolean).join(' ')
		];
		if (error.exc) {
			exception = error.exc;
			try {
				exception = JSON.parse(exception)[0];
				console.log(exception);
				// eslint-disable-next-line no-empty
			} catch (e) {}
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
			e.messages = error._error_message
				? [error._error_message]
				: ['Internal Server Error'];
		}
		updateState(this, null, e.messages.join('\n'));

		if (
			[401, 403].includes(res.status) &&
			router.currentRoute.name !== 'Login'
		) {
			router.push('/login');
		}
		throw e;
	}

	function updateState(vm, state, errorMessage) {
		if (vm?.state !== undefined) {
			vm.state = state;
		}
		if (vm?.errorMessage !== undefined) {
			vm.errorMessage = errorMessage;
		}
	}
}
