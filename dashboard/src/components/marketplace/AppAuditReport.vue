<script setup lang="ts">
import {
	AccordionContent,
	AccordionHeader,
	AccordionItem,
	AccordionRoot,
	AccordionTrigger,
} from 'reka-ui';
import {
	Badge,
	createResource,
	ErrorMessage,
	LoadingIndicator,
	Tooltip,
} from 'frappe-ui';
import dayjs from '@/utils/dayjs';
import { computed } from 'vue';
import {
	auditResultHeadline,
	formatDt,
	parseAuditCheckDetails,
	themeCheckResult,
	themeSeverity,
	type BadgeTheme,
} from '@/components/marketplace/auditor/utils';
import type {
	GetAppAuditResult,
	MarketplaceAppAuditCheckRow,
} from '@/components/marketplace/auditor/auditReportTypes';

const CATEGORY_ORDER = [
	'Metadata',
	'Versioning',
	'Dependencies',
	'Code Quality',
	'Security',
	'Compatibility',
	'Correctness',
	'Operational',
] as const;

const SEVERITY_ORDER: Record<string, number> = {
	Critical: 0,
	Major: 1,
	Minor: 2,
	Info: 3,
};

/** Sort after all known categories in `CATEGORY_ORDER` (indices 0..n). Arbitrary value. */
const UNKNOWN_CATEGORY_SORT = 999;
/**
 * Fallback ranks when ordering failing categories (lower = show first). Must be > Info (3). Arbitrary values.
 * Unknown label → 80; row has no severity → 100 (sorts after known severities). Arbitrary values.
 */
const UNKNOWN_SEVERITY_SORT = 80;
const NO_SEVERITY_SORT = 100;

const props = defineProps<{
	app: string;
}>();

const auditResource = createResource({
	url: 'press.api.marketplace.get_app_audit',
	method: 'GET',
	auto: true,
	params: {
		app: props.app,
	},
});

const doc = computed(() => auditResource.data as GetAppAuditResult);

const visibleChecks = computed(() =>
	(doc.value?.audit_checks ?? []).filter((row) => !row.is_internal_only),
);

// Checks grouped by category (each accordion is one category).
const byCategory = computed(() => {
	const grouped: Record<string, MarketplaceAppAuditCheckRow[]> = {};
	for (const row of visibleChecks.value) {
		(grouped[row.category] ??= []).push(row);
	}
	return grouped;
});

function categoryIndex(name: string): number {
	const i = (CATEGORY_ORDER as readonly string[]).indexOf(name);
	return i === -1 ? UNKNOWN_CATEGORY_SORT : i;
}

function categoryNeedsAttention(name: string): boolean {
	return (
		byCategory.value[name]?.some((r) =>
			['Fail', 'Warn', 'Error'].includes(r.result),
		) ?? false
	);
}

// for failing categories: sort by worst issue first (Critical before Major, etc.).
function worstIssueRank(name: string): number {
	let rank = UNKNOWN_CATEGORY_SORT;
	for (const r of byCategory.value[name] ?? []) {
		if (!['Fail', 'Warn', 'Error'].includes(r.result)) continue;
		const sev =
			r.severity != null
				? (SEVERITY_ORDER[r.severity] ?? UNKNOWN_SEVERITY_SORT)
				: NO_SEVERITY_SORT;
		rank = Math.min(rank, sev);
	}
	return rank;
}

// failing categories first (severity), then alphabetically by CATEGORY_ORDER.
const attentionCategories = computed(() =>
	Object.keys(byCategory.value)
		.filter(categoryNeedsAttention)
		.sort((a, b) => {
			const bySeverity = worstIssueRank(a) - worstIssueRank(b);
			return bySeverity !== 0
				? bySeverity
				: categoryIndex(a) - categoryIndex(b);
		}),
);

// passing-only categories: follow CATEGORY_ORDER for a consistent list.
const passedOnlyCategories = computed(() =>
	Object.keys(byCategory.value)
		.filter((c) => !categoryNeedsAttention(c))
		.sort((a, b) => categoryIndex(a) - categoryIndex(b)),
);

const accordionValue = (category: string) => `cat:${category}`;

const defaultOpenAttention = computed(() =>
	attentionCategories.value.map(accordionValue),
);

function categoryLabel(category: string): string {
	const rows = byCategory.value[category] ?? [];
	const fails = rows.filter(
		(r) => r.result === 'Fail' || r.result === 'Error',
	).length;
	const warns = rows.filter((r) => r.result === 'Warn').length;
	if (fails) return `${fails} failed`;
	if (warns) return `${warns} warning${warns === 1 ? '' : 's'}`;
	return 'Pass';
}

function categoryTheme(category: string): BadgeTheme {
	const rows = byCategory.value[category] ?? [];
	if (rows.some((r) => r.result === 'Fail' || r.result === 'Error'))
		return 'red';
	if (rows.some((r) => r.result === 'Warn')) return 'orange';
	return 'green';
}

function categoryWorstSeverity(category: string): string | undefined {
	let worst: string | undefined;
	let rank = 999;
	for (const r of byCategory.value[category] ?? []) {
		if (!['Fail', 'Warn', 'Error'].includes(r.result)) continue;
		const s = r.severity;
		if (!s) continue;
		const rk = SEVERITY_ORDER[s] ?? 99;
		if (rk < rank) {
			rank = rk;
			worst = s;
		}
	}
	return worst;
}

const worstSeverityByCategory = computed(() => {
	const m: Record<string, string> = {};
	for (const cat of Object.keys(byCategory.value)) {
		const s = categoryWorstSeverity(cat);
		if (s) m[cat] = s;
	}
	return m;
});

const appDisplayName = computed(
	// capitalize first letter and remove underscores
	() =>
		(doc.value?.marketplace_app || props.app)
			.replace(/_/g, ' ')
			.replace(/\b\w/g, (char) => char.toUpperCase()),
);

const checkStats = computed(() => {
	let pass = 0;
	let warn = 0;
	let fail = 0;
	let skipped = 0;
	let blocking = 0;
	for (const r of visibleChecks.value) {
		if (r.is_blocking) blocking += 1;
		if (r.result === 'Pass') pass += 1;
		else if (r.result === 'Warn') warn += 1;
		else if (r.result === 'Fail' || r.result === 'Error') fail += 1;
		else if (r.result === 'Skipped') skipped += 1;
	}
	return {
		pass,
		warn,
		fail,
		skipped,
		blocking,
		total: visibleChecks.value.length,
	};
});

const issueCount = computed(
	() => checkStats.value.fail + checkStats.value.warn,
);

const failSeveritySummary = computed(() => {
	const n = { Critical: 0, Major: 0, Minor: 0, Info: 0 };
	for (const r of visibleChecks.value) {
		if (r.result !== 'Fail' && r.result !== 'Error') continue;
		if (r.severity && r.severity in n) n[r.severity as keyof typeof n] += 1;
	}
	const parts: string[] = [];
	if (n.Critical) parts.push(`${n.Critical} Critical`);
	if (n.Major) parts.push(`${n.Major} Major`);
	if (n.Minor) parts.push(`${n.Minor} Minor`);
	if (n.Info) parts.push(`${n.Info} Info`);
	return parts.join(', ');
});

const runAt = computed(() => doc.value?.finished_at || doc.value?.started_at);
const runRelative = computed(() =>
	runAt.value ? `Ran ${dayjs(runAt.value).fromNow()}` : '',
);
const runExact = computed(() => formatDt(runAt.value));

const heroSurface = computed(() => {
	const st = doc.value?.status;
	if (st === 'Running' || st === 'Queued')
		return 'border-blue-200/90 bg-blue-50/80';
	if (st === 'Failed') return 'border-red-300/90 bg-red-50/90';
	const r = doc.value?.audit_result;
	if (r === 'Fail') return 'border-red-200/90 bg-red-50/85';
	if (r === 'Warn' || r === 'Needs Improvement')
		return 'border-amber-200/90 bg-amber-50/80';
	if (r === 'Pass') return 'border-green-200/80 bg-green-50/70';
	if (r === 'Inconclusive') return 'border-outline-gray-2 bg-surface-gray-2/50';
	return 'border-outline-gray-1 bg-surface-gray-2/40';
});

const heroTitleClass = computed(() => {
	const r = doc.value?.audit_result;
	if (r === 'Fail') return 'text-red-900';
	if (r === 'Warn' || r === 'Needs Improvement') return 'text-amber-950';
	if (r === 'Pass') return 'text-green-900';
	if (r === 'Inconclusive') return 'text-ink-gray-8';
	return 'text-ink-gray-9';
});

const nextStepsTooltip =
	'Review and fix the failing checks. Then push a new commit to your source branch to trigger a new audit.';

function remediationText(row: MarketplaceAppAuditCheckRow): string | undefined {
	const r = row.remediation;
	if (r == null) return undefined;
	const s = String(r).trim();
	return s || undefined;
}
</script>

<template>
	<div class="audit-report space-y-5">
		<div v-if="auditResource.loading" class="flex justify-center py-12">
			<div class="flex items-center gap-2 text-sm text-ink-gray-6">
				<LoadingIndicator class="h-4 w-4" />
				Loading audit…
			</div>
		</div>

		<ErrorMessage
			v-else-if="auditResource.error"
			:message="auditResource.error.message"
		/>

		<template v-else-if="auditResource.fetched">
			<p
				v-if="!doc"
				class="rounded-lg border border-outline-gray-1 bg-surface-gray-2/50 px-4 py-6 text-center text-sm text-ink-gray-6"
			>
				No audit has been run for this app yet.
			</p>

			<template v-else>
				<section
					id="audit-report-heading"
					class="scroll-mt-16 overflow-hidden rounded-lg border border-outline-gray-1 bg-surface-white shadow-xs"
					aria-labelledby="audit-summary-title"
				>
					<div class="border-b px-4 py-4 sm:px-5 sm:py-5" :class="heroSurface">
						<div
							class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"
						>
							<div class="min-w-0 space-y-2">
								<h2
									id="audit-summary-title"
									class="text-xl font-semibold leading-snug sm:text-[1.35rem]"
									:class="heroTitleClass"
								>
									{{ auditResultHeadline(doc.audit_result) }}
								</h2>
								<p class="text-sm leading-relaxed text-ink-gray-6">
									<template v-if="issueCount > 0">
										{{ issueCount }} issue{{ issueCount === 1 ? '' : 's' }} in
									</template>
									<template v-else>Latest audit for</template>
									<span class="font-medium text-ink-gray-9">{{
										appDisplayName
									}}</span>
								</p>
							</div>
							<div class="flex shrink-0 flex-col gap-2 text-sm sm:items-end">
								<time
									v-if="runRelative"
									class="text-ink-gray-6 cursor-default"
									:title="runExact"
									>{{ runRelative }}</time
								>
							</div>
						</div>
					</div>

					<div class="space-y-4 px-3.5 py-4 sm:px-5">
						<div v-if="checkStats.total" class="space-y-3">
							<div
								class="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm"
							>
								<span
									v-if="checkStats.pass > 0"
									class="font-medium text-green-800"
								>
									{{ checkStats.pass }} passed
								</span>
								<template
									v-if="
										checkStats.pass > 0 &&
										(checkStats.fail > 0 || checkStats.warn > 0)
									"
								>
									<span class="text-ink-gray-4">·</span>
								</template>
								<span
									v-if="checkStats.fail > 0"
									class="font-medium text-red-800"
									>{{ checkStats.fail }} failed</span
								>
								<template v-if="checkStats.warn > 0">
									<span v-if="checkStats.fail > 0" class="text-ink-gray-4"
										>·</span
									>
									<span class="font-medium text-amber-800">
										{{ checkStats.warn }} warning{{
											checkStats.warn === 1 ? '' : 's'
										}}
									</span>
								</template>
								<template v-if="checkStats.skipped > 0">
									<span class="text-ink-gray-4">·</span>
									<span class="text-ink-gray-7"
										>{{ checkStats.skipped }} skipped</span
									>
								</template>
								<span v-if="failSeveritySummary" class="text-ink-gray-5">
									({{ failSeveritySummary }})
								</span>
							</div>
							<div v-if="checkStats.blocking > 0" class="flex flex-wrap gap-2">
								<Badge
									:label="`${checkStats.blocking} blocking`"
									theme="red"
									size="sm"
								/>
							</div>
						</div>
					</div>
				</section>

				<section
					v-if="doc.status === 'Failed' && doc.error_traceback"
					class="scroll-mt-20 rounded-lg border border-red-200 bg-red-50/90 px-4 py-3"
					role="region"
					aria-label="Audit error details"
				>
					<div
						class="mb-2 flex items-center gap-2 text-sm font-medium text-red-900"
					>
						<lucide-alert-circle
							class="h-4 w-4 shrink-0 text-red-900"
							aria-hidden="true"
						/>

						Audit error
					</div>
					<pre
						class="max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-red-950"
						translate="no"
						>{{ doc.error_traceback }}</pre
					>
				</section>

				<section class="space-y-3" aria-labelledby="audit-checks-heading">
					<div class="flex flex-wrap items-center justify-between gap-2 px-1">
						<h3
							id="audit-checks-heading"
							class="text-base font-semibold text-ink-gray-9"
						>
							Check results
						</h3>
						<Tooltip
							v-if="issueCount > 0 && doc.status === 'Completed'"
							:text="nextStepsTooltip"
						>
							<button
								type="button"
								class="rounded p-1 text-ink-gray-4 transition-colors hover:bg-surface-gray-2 hover:text-ink-gray-7 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
								aria-label="What to do after a failed audit"
							>
								<lucide-help-circle class="h-4 w-4" aria-hidden="true" />
							</button>
						</Tooltip>
					</div>

					<AccordionRoot
						v-if="attentionCategories.length"
						type="multiple"
						class="flex flex-col gap-2"
						:default-value="defaultOpenAttention"
						:unmount-on-hide="false"
					>
						<AccordionItem
							v-for="cat in attentionCategories"
							:key="cat"
							:value="accordionValue(cat)"
							class="scroll-mt-20 overflow-hidden rounded-lg border border-outline-gray-1 bg-surface-white shadow-xs"
						>
							<AccordionHeader class="flex" as="h4">
								<AccordionTrigger
									as="button"
									type="button"
									class="group inline-flex min-h-[44px] w-full touch-manipulation items-center justify-between gap-3 px-4 py-3 text-left text-sm outline-none transition-colors hover:bg-surface-gray-2 focus-visible:bg-surface-gray-2"
								>
									<span
										class="flex min-w-0 flex-1 flex-wrap items-center gap-2"
									>
										<span class="font-medium text-ink-gray-9">{{ cat }}</span>
										<Badge
											v-if="worstSeverityByCategory[cat]"
											:label="worstSeverityByCategory[cat]"
											:theme="themeSeverity(worstSeverityByCategory[cat])"
											size="sm"
										/>
									</span>
									<span class="flex shrink-0 items-center gap-2">
										<Badge
											:label="categoryLabel(cat)"
											:theme="categoryTheme(cat)"
											size="sm"
										/>
										<lucide-chevron-down
											class="h-4 w-4 shrink-0 text-ink-gray-4 transition-transform duration-200 group-hover:text-ink-gray-6 group-data-[state=open]:rotate-180 motion-reduce:transition-none"
											aria-hidden="true"
										/>
									</span>
								</AccordionTrigger>
							</AccordionHeader>
							<AccordionContent
								class="audit-acc-content overflow-hidden border-t border-outline-gray-2 shadow-xs"
							>
								<div class="space-y-4 px-3 py-2">
									<div
										v-for="row in byCategory[cat]"
										:key="row.check_id"
										class="rounded-md bg-surface-gray-2/80 px-3 py-2.5"
									>
										<div
											class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"
										>
											<div class="min-w-0">
												<div class="flex flex-wrap items-center gap-2">
													<span class="text-sm font-medium text-ink-gray-9">{{
														row.check_name
													}}</span>
													<Badge
														v-if="row.is_blocking"
														label="Blocking"
														theme="red"
														size="sm"
													/>
												</div>
												<p
													v-if="row.message"
													class="mt-1 text-sm leading-relaxed text-ink-gray-7"
												>
													{{ row.message }}
												</p>
											</div>
											<div class="flex shrink-0 flex-wrap gap-1.5">
												<Badge
													:label="row.result"
													:theme="themeCheckResult(row.result)"
													size="sm"
												/>
												<Badge
													v-if="row.severity"
													:label="row.severity"
													:theme="themeSeverity(row.severity)"
													size="sm"
												/>
											</div>
										</div>

										<template v-if="row.details">
											<template
												v-for="parsed in [parseAuditCheckDetails(row.details)]"
												:key="`${row.check_id}-details`"
											>
												<div
													v-if="
														parsed.kind === 'occurrences' &&
														parsed.occurrences.length
													"
													class="mt-3 space-y-1.5"
												>
													<div
														v-for="(occ, id) in parsed.occurrences"
														:key="`${row.check_id}-${id}-${occ.rule_id}-${occ.path}-${occ.start?.line}`"
														class="rounded border border-outline-gray-2 bg-surface-gray-2/60 px-3 py-2.5"
													>
														<div v-if="occ.is_blocking" class="mb-2">
															<Badge label="Blocking" theme="red" size="sm" />
														</div>
														<p
															v-if="occ.rule_id"
															class="font-mono text-xs font-semibold leading-snug text-ink-gray-9"
														>
															{{ occ.rule_id }}
														</p>
														<p
															class="mt-0.5 [overflow-wrap:anywhere] font-mono text-[11px] leading-snug text-ink-gray-5"
														>
															{{ occ.path || '–' }}
															<template v-if="occ.start?.line != null">
																<span class="text-ink-gray-4"> · </span>line
																{{ occ.start.line }}
															</template>
														</p>
														<p
															v-if="occ.message"
															class="mt-2 text-xs text-ink-gray-8"
														>
															{{ occ.message }}
														</p>
													</div>
												</div>
												<pre
													v-else-if="parsed.kind === 'object'"
													class="mt-3 max-h-48 overflow-auto rounded border border-outline-gray-2 bg-surface-white p-2 font-mono text-xs text-ink-gray-8"
													translate="no"
													>{{ JSON.stringify(parsed.data, null, 2) }}</pre
												>
												<p
													v-else-if="parsed.kind === 'text'"
													class="mt-3 text-sm text-ink-gray-7"
												>
													{{ parsed.text }}
												</p>
											</template>
										</template>

										<div
											v-if="remediationText(row)"
											class="mt-4 border-l-[3px] border-l-green-600/70 pl-3"
										>
											<p class="mb-0.5 text-sm font-medium text-ink-gray-6">
												How to fix?
											</p>

											<p class="text-sm leading-relaxed text-ink-gray-7">
												{{ remediationText(row) }}
											</p>
										</div>
									</div>
								</div>
							</AccordionContent>
						</AccordionItem>
					</AccordionRoot>

					<details
						v-if="passedOnlyCategories.length"
						class="group overflow-hidden rounded-lg border border-outline-gray-1 bg-surface-white shadow-xs [&_summary::-webkit-details-marker]:hidden"
					>
						<summary
							class="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-left text-sm font-medium text-ink-gray-9 transition-colors hover:bg-surface-gray-2 focus-visible:bg-surface-gray-2"
						>
							<span>Passed checks ({{ passedOnlyCategories.length }})</span>
							<lucide-chevron-down
								class="h-4 w-4 shrink-0 text-ink-gray-4 transition-transform duration-200 group-open:rotate-180 motion-reduce:transition-none"
								aria-hidden="true"
							/>
						</summary>
						<div class="border-t border-outline-gray-2">
							<AccordionRoot
								type="multiple"
								class="flex flex-col gap-0"
								:default-value="[]"
								:unmount-on-hide="false"
							>
								<AccordionItem
									v-for="cat in passedOnlyCategories"
									:key="cat"
									:value="accordionValue(cat)"
									class="overflow-hidden border-b border-outline-gray-2 last:border-b-0"
								>
									<AccordionHeader class="flex" as="h4">
										<AccordionTrigger
											as="button"
											type="button"
											class="group inline-flex min-h-[44px] w-full touch-manipulation items-center justify-between gap-3 bg-surface-gray-2/30 px-4 py-3 text-left text-sm outline-none transition-colors hover:bg-surface-gray-2/60 focus-visible:bg-surface-gray-2/60"
										>
											<span class="font-medium text-ink-gray-9">{{ cat }}</span>
											<span class="flex shrink-0 items-center gap-2">
												<Badge label="Pass" theme="green" size="sm" />
												<lucide-chevron-down
													class="h-4 w-4 shrink-0 text-ink-gray-4 transition-transform duration-200 group-hover:text-ink-gray-6 group-data-[state=open]:rotate-180 motion-reduce:transition-none"
													aria-hidden="true"
												/>
											</span>
										</AccordionTrigger>
									</AccordionHeader>
									<AccordionContent
										class="audit-acc-content overflow-hidden border-t border-outline-gray-2 bg-surface-white"
									>
										<div class="space-y-4 px-4 py-3">
											<div
												v-for="row in byCategory[cat]"
												:key="row.check_id"
												class="rounded-md bg-surface-gray-2/80 px-3 py-2.5"
											>
												<div
													class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between"
												>
													<div class="min-w-0">
														<span class="text-sm font-medium text-ink-gray-9">{{
															row.check_name
														}}</span>
														<p
															v-if="row.message"
															class="mt-1 text-sm leading-relaxed text-ink-gray-7"
														>
															{{ row.message }}
														</p>
													</div>
													<Badge
														:label="row.result"
														:theme="themeCheckResult(row.result)"
														size="sm"
													/>
												</div>
												<div
													v-if="remediationText(row)"
													class="mt-3 border-l-[3px] border-l-green-600/70 pl-3"
												>
													<p class="mb-0.5 text-sm font-medium text-ink-gray-6">
														How to fix
													</p>

													<p class="text-sm leading-relaxed text-ink-gray-7">
														{{ remediationText(row) }}
													</p>
												</div>
											</div>
										</div>
									</AccordionContent>
								</AccordionItem>
							</AccordionRoot>
						</div>
					</details>

					<p
						v-if="!attentionCategories.length && !passedOnlyCategories.length"
						class="rounded-lg border border-outline-gray-1 bg-surface-gray-2/30 px-4 py-3 text-sm text-ink-gray-6"
					>
						No check rows on this audit yet.
					</p>
				</section>
			</template>
			<p class="text-center text-xs text-ink-gray-4" role="status">
				This is an automated audit report generated by FC Marketplace Auditor
				(beta). If you believe this report is incorrect or need help
				interpreting it, reach out to
				<a href="https://support.frappe.io" class="underline"
					>support.frappe.io</a
				>.
			</p>
		</template>
	</div>
</template>

<style scoped>
@keyframes audit-acc-down {
	from {
		height: 0;
	}

	to {
		height: var(--reka-accordion-content-height);
	}
}

@keyframes audit-acc-up {
	from {
		height: var(--reka-accordion-content-height);
	}

	to {
		height: 0;
	}
}

.audit-acc-content[data-state='open'] {
	animation: audit-acc-down 200ms ease-out;
}

.audit-acc-content[data-state='closed'] {
	animation: audit-acc-up 200ms ease-out;
}
</style>
