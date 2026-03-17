<template>
	<div class="mx-auto max-w-3xl px-5 py-8 w-full">
		<!-- Search bar: history only -->
		<div v-if="isHistory" class="mb-6">
			<FormControl
				type="text"
				placeholder="Search past incidents..."
				v-model="searchQuery"
				:prefix-icon="'search'"
			/>
		</div>

		<div v-if="$resources.incidents.loading" class="flex justify-center py-12">
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
				<FeatherIcon name="archive" class="h-8 w-8 text-ink-gray-4" />
			</div>
			<div
				v-else
				class="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-surface-green-1"
			>
				<FeatherIcon name="check" class="h-8 w-8 text-ink-green-2" />
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

		<div v-else>
			<!-- Header: ongoing only -->
			<div v-if="!isHistory" class="mb-4 flex items-center justify-between">
				<span>Active Incidents ({{ incidentCount }})</span>
				<Button variant="ghost" size="sm" @click="refresh">
					<template #prefix>
						<FeatherIcon name="refresh-cw" class="h-3.5 w-3.5" />
					</template>
					Refresh
				</Button>
			</div>

			<div v-for="tree in incidentTrees" :key="tree.id" class="mb-1 px-2 py-1">
				<Tree
					:node="tree"
					nodeKey="id"
					:options="{
						defaultCollapsed: isHistory,
						showIndentationGuides: true,
						indentWidth: '16px',
						rowHeight: '28px',
					}"
				>
					<template #label="{ node }">
						<!-- Incident root node -->
						<div
							v-if="node.type === 'incident'"
							class="items-center justify-between flex gap-2 py-0.5 w-full"
						>
							<span>{{ node.server }}</span>
							<span class="text-ink-gray-4">· {{ node.status }}</span>
						</div>
						<!-- Timeline group -->
						<div
							v-else-if="node.type === 'timeline-group'"
							class="flex items-center gap-2 py-0.5"
						>
							<FeatherIcon name="clock" class="h-3.5 w-3.5 shrink-0" />
							<span>Timeline</span>
						</div>
						<!-- Timeline step -->
						<div
							v-else-if="node.type === 'timeline-step'"
							class="flex items-center gap-2 py-0.5 w-full"
						>
							<FeatherIcon
								:name="node.icon"
								:class="['h-3.5 w-3.5 shrink-0', node.iconClass]"
							/>
							<span>{{ node.label }}</span>
							<span class="ml-auto shrink-0 text-ink-gray-4">{{
								node.time
							}}</span>
						</div>
						<!-- Investigation node -->
						<div
							v-else-if="node.type === 'investigation'"
							class="flex items-center gap-2 py-0.5"
						>
							<FeatherIcon name="zap" class="h-3.5 w-3.5 shrink-0" />
							<span>Investigation - {{ node.status }}</span>
						</div>
						<!-- Findings group (Server / Database) -->
						<div
							v-else-if="node.type === 'findings-group'"
							class="flex items-center gap-2 py-0.5"
						>
							<FeatherIcon
								:name="node.label === 'Server' ? 'server' : 'database'"
								class="h-3.5 w-3.5 shrink-0"
							/>
							<span>{{ node.label }}</span>
						</div>
						<!-- Individual finding step -->
						<div
							v-else-if="node.type === 'finding-step'"
							class="flex items-center gap-2 py-0.5 w-full"
						>
							<div class="flex items-center gap-2 w-full">
								<span class="truncate min-w-0">{{ node.label }}</span>
								<div
									v-if="node.isUnableToInvestigate"
									class="ml-auto shrink-0 flex items-center gap-[5px]"
								>
									<FeatherIcon name="slash" class="h-3 w-3 text-ink-gray-4" />
									<span class="text-ink-gray-4">Unable To Investigate</span>
								</div>
								<div
									v-else-if="node.isLikelyCause"
									class="ml-auto shrink-0 flex items-center gap-[5px]"
								>
									<FeatherIcon
										name="alert-triangle"
										class="h-3 w-3 text-ink-amber-3"
									/>
									<span class="text-ink-amber-3">Likely Cause</span>
								</div>
								<div
									v-else
									class="ml-auto shrink-0 flex items-center gap-[5px]"
								>
									<FeatherIcon
										name="check-circle"
										class="h-3 w-3 text-ink-green-2"
									/>
									<span class="text-ink-green-2">Passed</span>
								</div>
							</div>
						</div>
						<!-- Action step -->
						<div
							v-else-if="node.type === 'action-step'"
							class="flex items-center gap-2 py-0.5 w-full"
						>
							<span class="truncate min-w-0"
								>{{ node.label }} - {{ node.status }}</span
							>
						</div>
						<!-- Generic fallback -->
						<span v-else>{{ node.label }}</span>
					</template>
				</Tree>
			</div>
		</div>
	</div>
</template>

<script>
import { FeatherIcon, Button, Tree, FormControl } from 'frappe-ui';

export default {
	name: 'Incidents',
	components: {
		FeatherIcon,
		Button,
		Tree,
		FormControl,
	},
	data() {
		return {
			searchQuery: '',
		};
	},
	resources: {
		incidents() {
			return {
				url: 'press.api.incident.get_incidents',
				params: this.isHistory ? { resolved: true } : {},
				auto: true,
			};
		},
	},
	computed: {
		isHistory() {
			return this.$route.name === 'IncidentHistory';
		},
		hasNoIncidents() {
			const data = this.$resources.incidents.data;
			return !this.$resources.incidents.loading && (!data || data.length === 0);
		},
		incidentCount() {
			return this.$resources.incidents.data?.length || 0;
		},
		filteredData() {
			const data = this.$resources.incidents.data || [];
			if (!this.isHistory || !this.searchQuery) return data;
			const query = this.searchQuery.toLowerCase();
			return data.filter(
				(incident) =>
					incident.server?.toLowerCase().includes(query) ||
					incident.name?.toLowerCase().includes(query),
			);
		},
		incidentTrees() {
			return this.filteredData.map((incident) => {
				const children = [];

				// Timeline
				const timelineSteps = [];
				if (incident.creation) {
					timelineSteps.push({
						type: 'timeline-step',
						label: 'Created',
						time: this.formatDate(incident.creation),
						icon: 'alert-circle',
						iconClass: 'text-ink-gray-4',
					});
				}
				if (incident.confirmed_at) {
					timelineSteps.push({
						type: 'timeline-step',
						label: 'Confirmed',
						time: this.formatDate(incident.confirmed_at),
						icon: 'check-circle',
						iconClass: 'text-ink-amber-3',
					});
				}
				if (incident.resolved_at) {
					timelineSteps.push({
						type: 'timeline-step',
						label: 'Resolved',
						time: this.formatDate(incident.resolved_at),
						icon: 'check-circle',
						iconClass: 'text-ink-green-2',
					});
				}
				if (timelineSteps.length) {
					children.push({
						type: 'timeline-group',
						label: 'Timeline',
						children: timelineSteps,
					});
				}

				// Investigation
				if (incident.investigation_name) {
					const findings = incident.investigation_findings
						? JSON.parse(incident.investigation_findings)
						: [];
					const grouped = findings.reduce((acc, step) => {
						(acc[step.step_type] ||= []).push(step);
						return acc;
					}, {});
					const findingChildren = Object.entries(grouped).map(
						([groupLabel, steps]) => ({
							label: groupLabel,
							type: 'findings-group',
							children: steps.map((step, idx) => ({
								id: `${incident.name}__inv__${groupLabel}__${idx}`,
								label: step.step_name,
								type: 'finding-step',
								isLikelyCause: step.is_likely_cause,
								isUnableToInvestigate: step.is_unable_to_investigate,
							})),
						}),
					);
					children.push({
						label: incident.investigation_name,
						type: 'investigation',
						status: incident.investigation_status,
						children: findingChildren,
					});
				}

				// Action steps
				if (incident.investigation_action_steps) {
					const actionSteps = incident.investigation_action_steps.split(',');
					const actionChildren = actionSteps.map((step, idx) => ({
						label: step,
						type: 'action-step',
						status: incident.investigation_action_steps_status
							? incident.investigation_action_steps_status.split(',')[idx]
							: 'Unknown',
					}));
					children.push({
						label: 'Action Taken',
						type: 'actions-group',
						children: actionChildren,
					});
				}

				return {
					id: incident.name,
					label: incident.name,
					type: 'incident',
					status: incident.status,
					server: incident.server,
					children,
				};
			});
		},
	},
	watch: {
		// Re-fetch when navigating between routes
		isHistory() {
			this.$resources.incidents.reload();
			this.searchQuery = '';
		},
	},
	methods: {
		refresh() {
			this.$resources.incidents.reload();
		},
		formatDate(dateStr) {
			if (!dateStr) return '';
			return new Date(dateStr).toLocaleString(undefined, {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
			});
		},
	},
};
</script>
