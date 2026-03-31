<template>
	<div class="mx-auto max-w-3xl px-5 py-8 w-full">
		<!-- Search bar: history only -->
		<div v-if="isHistory" class="mb-6" :class="{ invisible: hasNoIncidents }">
			<FormControl
				type="text"
				placeholder="Search past incidents..."
				v-model="searchQuery"
				:prefix-icon="'search'"
			>
				<template #prefix>
					<LucideSearch class="size-3.5 text-ink-gray-6 p-0" />
				</template>
			</FormControl>
		</div>

		<!-- Header: ongoing only -->
		<div
			v-else
			class="mb-4 flex items-center justify-between"
			:class="{ invisible: hasNoIncidents }"
		>
			<div class="flex items-center gap-2">
				<span class="text-base">Active Incidents</span>
				<Badge
					class="rounded-sm"
					:label="incidentCount.data"
					v-if="incidentCount.data"
				/>
			</div>

			<Button size="sm" @click="refresh" variant="solid">
				<template #prefix>
					<LucideRefreshCw class="size-4" />
				</template>
				Refresh
			</Button>
		</div>

		<div
			v-if="incidents.loading"
			class="flex gap-3 justify-center items-center p-20 border rounded fade-in"
		>
			<LucideSpinner class="size-4 animate-spin" />
			Loading...
		</div>

		<!-- Empty state -->
		<div
			v-else-if="hasNoIncidents"
			class="flex flex-col items-center justify-center py-20 text-center"
		>
			<div
				v-if="isHistory"
				class="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-surface-gray-2"
			>
				<LucideArchive class="h-8 w-8 text-ink-gray-4" />
			</div>
			<div
				v-else
				class="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-surface-green-1"
			>
				<LucideCheck class="h-8 w-8 text-ink-green-2" />
			</div>
			<h3>
				{{ isHistory ? 'No incident history' : 'All systems operational' }}
			</h3>
			<p class="mt-2">
				{{
					isHistory
						? 'When incidents are resolved, they will appear here.'
						: 'There are no active incidents affecting your sites or servers.'
				}}
			</p>
		</div>

		<template v-else>
			<template
				v-for="(incident, i) in incidentTrees"
				:key="incident.id || 'dummyInc' + i"
			>
				<IncidentCard v-if="incident.server" :data="incident" />
				<div v-else class="p-3.5 text-sm mb-5 border invisible">k</div>
			</template>

			<Pagination
				v-if="Number(incidentCount.data)"
				:total-pages="incidentCount.data"
				:limit="limit"
				v-model:page="currentPage"
				class="w-fit mx-auto fade-in"
			/>
		</template>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Badge, Button, FormControl, createResource } from 'frappe-ui';
import { useRoute } from 'vue-router';
import LucideRefreshCw from '~icons/lucide/refresh-cw';
import LucideSpinner from '~icons/lucide/loader-circle';
import IncidentCard from './IncidentCard.vue';
import Pagination from '@/components/common/Pagination.vue';

const currentPage = ref(1);
const limit = 10;

defineOptions({ name: 'IncidentHistory' });

const searchQuery = ref('');

const route = useRoute();
const isHistory = computed(() => route.name == 'IncidentHistory');

const hasNoIncidents = computed(
	() => !incidents.loading && (!incidents.data || incidents.data.length === 0),
);

const filteredData = computed(() => {
	const data = incidents.data || [];
	if (!isHistory.value || !searchQuery.value) return data;

	const query = searchQuery.value.toLowerCase();

	return data.filter(
		(incident) =>
			incident?.server?.toLowerCase().includes(query) ||
			incident?.name?.toLowerCase().includes(query),
	);
});

const incidentTrees = computed(() =>
	filteredData.value.map((incident) => {
		// Timeline
		const timelineSteps = [];
		if (incident?.creation) {
			timelineSteps.push({
				type: 'timeline-step',
				label: 'Created',
				time: formatDate(incident.creation),
			});
		}
		if (incident?.confirmed_at) {
			timelineSteps.push({
				label: 'Confirmed',
				time: formatDate(incident.confirmed_at),
			});
		}
		if (incident?.resolved_at) {
			timelineSteps.push({
				type: 'timeline-step',
				label: 'Resolved',
				time: formatDate(incident.resolved_at),
			});
		}

		// Investigation
		let investigation = null;
		if (incident?.investigation_name) {
			const findings = incident.investigation_findings
				? typeof incident.investigation_findings === 'string'
					? JSON.parse(incident.investigation_findings)
					: incident.investigation_findings
				: [];
			const grouped = findings.reduce((acc, step) => {
				(acc[step.step_type] ||= []).push(step);
				return acc;
			}, {});
			investigation = {
				name: incident.investigation_name,
				status: incident.investigation_status,
				groups: Object.entries(grouped).map(([label, steps]) => ({
					label,
					steps,
				})),
			};
		}

		// Action steps
		let actionSteps = null;
		if (incident?.investigation_action_steps) {
			const labels = incident.investigation_action_steps
				.split(',')
				.map((s) => s.trim());
			const statuses = incident.investigation_action_steps_status
				? incident.investigation_action_steps_status
						.split(',')
						.map((s) => s.trim())
				: [];
			actionSteps = labels.map((label, idx) => ({
				label,
				status: statuses[idx] || 'Unknown',
			}));
		}

		return {
			id: incident?.name,
			server: incident?.server,
			status: incident?.status,
			timelineSteps,
			investigation,
			actionSteps,
		};
	}),
);

const incidents = createResource({
	url: 'press.api.incident.get_incidents',
	makeParams: () => {
		return { page: currentPage.value, limit, resolved: isHistory.value };
	},
	transform: (data) => {
		if (data.length !== 0 && data.length < limit) {
			const dataToAdd = limit - data.length;
			data.push(...Array(dataToAdd).fill(null));
			return data;
		}
	},
	auto: true,
});

const incidentCount = createResource({
	url: 'press.api.incident.get_incident_count',
	params: {
		resolved: isHistory.value,
	},
	auto: true,
});

watch(isHistory, () => {
	incidents.fetch();
	searchQuery.value = '';
});

watch(currentPage, () => {
	incidents.fetch();
});

const refresh = () => incidents.reload();
const formatDate = (dateStr: string) => {
	if (!dateStr) return '';
	return new Date(dateStr).toLocaleString(undefined, {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
		year: 'numeric',
	});
};
</script>

<style scoped>
.fade-in {
	animation: fadeIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeIn {
	from {
		opacity: 0;
	}
	to {
		opacity: 1;
	}
}
</style>
