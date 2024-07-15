import type { Platform } from '../types';

export function getPlatform(): Platform {
	const ua = navigator.userAgent.toLowerCase();

	if (ua.indexOf('win') > -1) {
		return 'win';
	} else if (ua.indexOf('mac') > -1) {
		return 'mac';
	} else if (ua.indexOf('x11') > -1 || ua.indexOf('linux') > -1) {
		return 'linux';
	}

	return 'unknown';
}

export function isMobile(): boolean {
	return window.innerWidth < 640;
}
