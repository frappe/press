export default async function call(method, args) {
	if (!args) {
		args = {};
	}

	const res = await fetch(`/api/method/${method}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json; charset=utf-8',
            'X-Frappe-Site-Name': window.location.hostname
		},
		body: JSON.stringify(args)
	});

	if (res.ok) {
		const data = await res.json();
		if (data.docs) {
			return data;
		}
		return data.message;
	} else {
		let error = null;
		let data = null;
		try {
			data = await res.json();
			if (data.exc) {
				error = JSON.parse(data.exc)[0];
			}
		} catch (e) {
			error = await res.text();
		}
		console.error(error);
		return {
			error: true,
			data
		};
	}
}
