export async function trypromise(promise) {
	try {
		let data = await promise;
		return [null, data];
	} catch (error) {
		return [error, null];
	}
}

export function getQueryParam(name) {
	try {
		let params = new URLSearchParams(window.location.search);
		return params.get(name);
	} catch (error) {
		return null;
	}
}

export function setQueryParam(name, value) {
	try {
		let params = new URLSearchParams(window.location.search);
		if (value === null || value === undefined) {
			params.delete(name);
		} else {
			params.set(name, value);
		}
		window.history.replaceState(
			{},
			'',
			`${window.location.pathname}?${params}`,
		);
	} catch (error) {
		console.error('Failed to set query param:', error);
	}
	// Note: This function does not handle the case where the URL is malformed.
}
