import dayjs from 'dayjs';
import type { AuditOccurrence } from './auditReportTypes';

export type BadgeTheme = 'gray' | 'blue' | 'green' | 'orange' | 'red';

export function auditResultHeadline(result: string | undefined): string {
	if (!result) return 'Audit Report';
	const m: Record<string, string> = {
		Pass: 'Audit Passed',
		'Needs Improvement': 'Needs Improvement',
		Warn: 'Audit Passed with Warnings',
		Fail: 'Audit Failed',
		Inconclusive: 'Audit Inconclusive',
	};
	return m[result] ?? result;
}

export type ParsedAuditDetails =
	| { kind: 'occurrences'; occurrences: AuditOccurrence[] }
	| { kind: 'object'; data: Record<string, unknown> }
	| { kind: 'text'; text: string }
	| { kind: 'none' };

function isTruthyInternalOnly(v: unknown): boolean {
	if (v === true || v === 1) return true;
	return false;
}

export function parseAuditCheckDetails(raw: string | null | undefined): ParsedAuditDetails {
	if (!raw || String(raw).trim() === '') return { kind: 'none' };
	const s = String(raw).trim();

	let data: unknown;
	try {
		data = JSON.parse(s);
	} catch {
		return { kind: 'text', text: s };
	}

	if (data && typeof data === 'object' && !Array.isArray(data)) {
		const obj = data as Record<string, unknown>;
		const occ = obj.occurrences;
		if (Array.isArray(occ)) {
			const occurrences = occ
				.filter((o): o is Record<string, unknown> => o != null && typeof o === 'object')
				.map((o) => o as AuditOccurrence)
				.filter((o) => !isTruthyInternalOnly(o.is_internal_only));
			return { kind: 'occurrences', occurrences };
		}
		return { kind: 'object', data: obj };
	}

	return { kind: 'text', text: s };
}

export function formatDt(value: string | null | undefined): string {
	if (!value) return '—';
	return dayjs(value).format('MMM D, YYYY h:mm A');
}

export function themeStatus(status: string | undefined): BadgeTheme {
	const m: Record<string, BadgeTheme> = {
		Queued: 'gray',
		Running: 'blue',
		Completed: 'green',
		Failed: 'red',
	};
	return m[status ?? ''] ?? 'gray';
}

export function themeAuditResult(result: string | undefined): BadgeTheme {
	if (!result) return 'gray';
	const m: Record<string, BadgeTheme> = {
		Pass: 'green',
		'Needs Improvement': 'orange',
		Warn: 'orange',
		Fail: 'red',
		Inconclusive: 'gray',
	};
	return m[result] ?? 'gray';
}

export function themeCheckResult(result: string): BadgeTheme {
	const m: Record<string, BadgeTheme> = {
		Pass: 'green',
		Warn: 'orange',
		Fail: 'red',
		Skipped: 'gray',
		Error: 'red',
	};
	return m[result] ?? 'gray';
}

export function themeSeverity(severity: string | undefined): BadgeTheme {
	if (!severity) return 'gray';
	const m: Record<string, BadgeTheme> = {
		Critical: 'red',
		Major: 'orange',
		Minor: 'orange',
		Info: 'blue',
	};
	return m[severity] ?? 'gray';
}
