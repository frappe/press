// Pulse analytics for the dashboard SPA. Config comes from dashboard boot
// (window.pulse_telemetry); the shared pulse_client.js is loaded from the Pulse
// host at runtime — cloud.frappe.io's framework predates the bundled client.
const DEFAULT_PULSE_CLIENT_URL =
	'https://pulse.m.frappe.cloud/assets/pulse/js/pulse_client.js';

// The anonymous id forwarded from the product website as ?aid=…. Pulse's cookieless
// anon id hashes the site into it, so events captured here get a different id than
// the visitor's pre-signup browsing on the website. Holding on to the forwarded one
// and sending it as the guest's distinct id keeps the whole funnel on a single id —
// the same id `signup` hands to the server to alias onto the team it creates.
const ANONYMOUS_ID_KEY = 'pulse:aid';
// Only has to outlive one signup attempt (verification email, Google redirect).
const ANONYMOUS_ID_TTL = 60 * 60 * 1000;

export function rememberAnonymousId() {
	const id = new URLSearchParams(window.location.search).get('aid');
	if (!id) return;
	try {
		window.localStorage.setItem(
			ANONYMOUS_ID_KEY,
			JSON.stringify({ id, at: Date.now() }),
		);
	} catch (error) {
		// storage unavailable — the signup just won't stitch
	}
}

export function getAnonymousId() {
	try {
		const stored = JSON.parse(
			window.localStorage.getItem(ANONYMOUS_ID_KEY) || 'null',
		);
		if (!stored) return null;
		if (Date.now() - stored.at > ANONYMOUS_ID_TTL) {
			forgetAnonymousId();
			return null;
		}
		return stored.id;
	} catch (error) {
		return null;
	}
}

export function forgetAnonymousId() {
	try {
		window.localStorage.removeItem(ANONYMOUS_ID_KEY);
	} catch (error) {
		// nothing to clean up
	}
}

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
		rememberAnonymousId();
		try {
			const mod = await import(/* @vite-ignore */ config.client_url || DEFAULT_PULSE_CLIENT_URL);
			this.client = new mod.PulseClient({
				host: config.host,
				apiKey: config.key,
				site: config.site,
				enabled: true,
				// A guest mid-signup has no user; ride the forwarded website id instead
				// so the signup funnel and the browsing before it are one identity.
				user: config.user || getAnonymousId() || undefined,
				team: config.team,
			});
			await this.client.init();
			this.flushPending();
			// Booting with a team means the signup went through and the server has
			// already aliased the id onto it — nothing left to keep it for.
			if (config.team) forgetAnonymousId();
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
