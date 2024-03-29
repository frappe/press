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

let runningJobs = reactive({});
export function subscribeToJobUpdates(socket) {
	socket.on('agent_job_update_for_site', data => {
		let job = runningJobs[data.id];
		if (!job) {
			job = data;
			runningJobs[data.id] = job;
		}
		Object.assign(job, data);
	});
}

export function getRunningJobs({ id, name, site, bench, server }) {
	if (id) {
		return runningJobs[id];
	}
	if (name) {
		return Object.values(runningJobs).filter(job => job.name === name);
	}
	if (site) {
		return Object.values(runningJobs).filter(job => job.site === site);
	}
	if (bench) {
		return Object.values(runningJobs).filter(job => job.bench === bench);
	}
	if (server) {
		return Object.values(runningJobs).filter(job => job.server === server);
	}
	return runningJobs;
}
