/** One Semgrep (or similar) finding inside `details.occurrences` JSON. */
export interface AuditOccurrence {
	rule_id?: string;
	path?: string;
	start?: { line?: number; col?: number; offset?: number };
	message?: string;
	severity?: string;
	is_blocking?: boolean | number;
	is_internal_only?: boolean | number;
}

/** Row from child table `audit_checks` (as returned by `as_dict()`). */
export interface MarketplaceAppAuditCheckRow {
	check_id: string;
	check_name: string;
	category: string;
	result: string;
	severity?: string;
	message?: string | null;
	details?: string | null;
	remediation?: string | null;
	is_internal_only?: number | boolean;
	is_blocking?: number | boolean;
}

export interface MarketplaceAppAuditDoc {
	name: string;
	doctype?: string;
	owner?: string;
	creation?: string;
	modified?: string;
	marketplace_app?: string;
	app_release?: string | null;
	approval_request?: string | null;
	team?: string | null;
	audit_type?: string;
	status?: string;
	audit_result?: string;
	audit_summary?: string | null;
	started_at?: string | null;
	finished_at?: string | null;
	error_traceback?: string | null;
	audit_checks?: MarketplaceAppAuditCheckRow[];
}

export type GetAppAuditResult = MarketplaceAppAuditDoc | null;
