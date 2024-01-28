import { frappeRequest } from 'frappe-ui';
import { reactive } from 'vue';

let states = {};

export function pollJobStatus(jobId, stopFunction) {
	if (!states[jobId]) {
		states[jobId] = reactive({ status: null, loading: false });
	}
	let state = states[jobId];
	state.loading = true;
	fetchJobStatus(jobId).then(status => {
		state.status = status;
	});
	if (stopFunction(state.status)) {
		state.loading = false;
		return;
	}
	setTimeout(() => {
		pollJobStatus(jobId, stopFunction);
	}, 1000);
	return state;
}

function fetchJobStatus(jobId) {
	return frappeRequest({
		url: 'press.api.site.get_job_status',
		params: { job_name: jobId }
	}).then(result => result.status);
}
