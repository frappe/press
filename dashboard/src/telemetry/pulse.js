// Pulse analytics for the dashboard SPA. Config comes from dashboard boot
// (window.pulse_telemetry); the shared pulse_client.js is loaded from the Pulse
// host at runtime — cloud.frappe.io's framework predates the bundled client.
const DEFAULT_PULSE_CLIENT_URL =
	'https://pulse.m.frappe.cloud/assets/pulse/js/pulse_client.js';

class PulseProvider {
	constructor() {
		this.enabled = false;
		this.client = null;
		// buffers events captured during the async client import
		this.pending = [];
	}

	async init(config) {
		if (!config?.enabled) return;
		this.enabled = true;
		try {
			const mod = await import(/* @vite-ignore */ config.client_url || DEFAULT_PULSE_CLIENT_URL);
			this.client = new mod.PulseClient({
				host: config.host,
				apiKey: config.key,
				site: config.site,
				enabled: true,
				user: config.user,
				team: config.team,
			});
			await this.client.init();
			this.flushPending();
		} catch (error) {
			this.enabled = false;
			this.pending = [];
		}
	}

	// Never throws: telemetry must not break the flow it rides on (signup, site creation).
	capture(event, props = {}) {
		try {
			if (!this.enabled) return;
			// app stays "press" across the dashboard; the funnel stage is the event name
			if (this.client) this.client.capture(event, 'press', props);
			else this.pending.push([event, props]);
		} catch (error) {
			// drop it
		}
	}

	flushPending() {
		const pending = this.pending;
		this.pending = [];
		pending.forEach(([event, props]) => this.capture(event, props));
	}
}

export const pulse = new PulseProvider();
