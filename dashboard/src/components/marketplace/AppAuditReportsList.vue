<script setup lang="ts">
import {
	Badge,
	Button,
	createResource,
	ErrorMessage,
	ListView,
} from "frappe-ui";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppAuditReport from "@/components/marketplace/AppAuditReport.vue";
import {
	formatDt,
	themeAuditResult,
	themeStatus,
} from "@/components/marketplace/auditor/utils";

interface AuditSummary {
	name: string;
	app_source: string;
	app_release: string;
	audit_type: string;
	audit_result: string;
	status: string;
	started_at: string | null;
	finished_at: string | null;
	source_version: string | null;
}

const props = defineProps<{ app: string }>();
const route = useRoute();
const router = useRouter();

const selectedAudit = computed(() => (route.query.audit as string) || null);

const auditReportsResource = createResource({
	url: "press.api.marketplace.get_app_audits",
	method: "GET",
	params: { app: props.app },
	auto: true,
});

const columns = [
	{ label: "Source", fieldname: "source_label", width: 1.4 },
	{ label: "Audit Type", fieldname: "audit_type", width: 0.9 },
	{ label: "Finished On", fieldname: "run_at", width: 1 },
	{ label: "Status", fieldname: "status", width: 0.7 },
	{ label: "Result", fieldname: "audit_result", width: 0.7 },
];

const rows = computed(() =>
	((auditReportsResource.data as AuditSummary[] | undefined) ?? []).map(
		(a) => ({
			...a,
			source_label: a.source_version
				? `${a.source_version} · ${a.app_source}`
				: a.app_source || "—",
			run_at: formatDt(a.finished_at || a.started_at),
		}),
	),
);

const openAudit = (row: AuditSummary) => {
	router.push({ query: { ...route.query, audit: row.name } });
};

const closeAudit = () => {
	const { audit: _, ...rest } = route.query;
	router.push({ query: rest });
}
</script>

<template>
	<div class="space-y-4">
		<template v-if="selectedAudit">
			<div class="flex items-center justify-end">
				<Button label="Back to audits" @click="closeAudit">
					<template #prefix>
						<lucide-arrow-left class="h-4 w-4" />
					</template>
				</Button>
			</div>
			<AppAuditReport :key="selectedAudit" :app="app" :audit-name="selectedAudit" />
		</template>

		<template v-else>
			<div class="flex items-center justify-end">
				<Button
					label="Refresh"
					:loading="auditReportsResource.loading"
					@click="auditReportsResource.reload()"
				>
					<template #prefix>
						<lucide-refresh-ccw class="h-4 w-4" />
					</template>
				</Button>
			</div>

			<ErrorMessage
				v-if="auditReportsResource.error"
				:message="auditReportsResource.error.message"
			/>

			<div v-else>
				<ListView
					:columns="columns"
:rows="rows"
					:options="{
						selectable: false,
						emptyState: {},
	onRowClick: openAudit,
					}"
					row-key="name"
				>
					<template #cell="{ row, column }">
						<span
							v-if="column.fieldname === 'source_label'"
class="truncate text-sm text-ink-gray-9">
							{{ row.source_label }}
						</span>
						<Badge
							v-else-if="column.fieldname === 'audit_result'"
							:label="row.audit_result || 'Pending'"
							:theme="themeAuditResult(row.audit_result)"
							size="sm"
						/>
						<Badge
							v-else-if="column.fieldname === 'status'"
							:label="row.status || 'Queued'"
							:theme="themeStatus(row.status)"
							size="sm"
/>
						<span v-else class="text-sm text-ink-gray-7">
							{{ row[column.fieldname] || '—' }}
						</span>
					</template>
				</ListView>

				<div v-if="!rows.length" class="px-5 py-8 text-center text-sm text-ink-gray-5"
				>
					<template v-if="auditReportsResource.loading">
						Loading audit reports...
					</template>
					<template v-else>No audit reports found for this app.</template>
				</div>
			</div>
		</template>
	</div>
</template>
