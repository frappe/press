<template>
	<Dialog
		:options="{
			title: 'Migrate Site',
			actions: selectedMigrationMode
				? [
						{
							label: selectedMigrationChoiceDetails?.button_label || 'Proceed',
							variant: 'solid',
							onClick: triggerMigration,
						},
					]
				: [],
		}"
		v-model="show"
		@close="resetValues"
	>
		<template #body-content>
			<div class="flex flex-col gap-3">
				<!-- Chose Migration Mode -->
				<div class="flex flex-col gap-2">
					<p class="text-base text-gray-800">Select Migration Type</p>
					<FormControl
						type="select"
						:options="migrationChoices"
						size="md"
						variant="outline"
						placeholder="Select Migration Option"
						v-model="selectedMigrationMode"
						required
					/>
				</div>
				<!-- Show description -->
				<p v-if="selectedMigrationMode" class="text-sm text-gray-700">
					{{ selectedMigrationChoiceDetails?.description }}
				</p>
				<!-- Update Site Migration -->
				<div v-if="selectedMigrationMode == 'Update Site'">
					<GenericList :options="updateSiteListOptions" />
				</div>

				<!-- Scheduling Option -->
				<DateTimeControl
					v-if="showSchedulingOption"
					v-model="scheduledTime"
					label="Schedule Time in IST"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { getCachedDocumentResource, Select } from 'frappe-ui';
import AlertBanner from '../AlertBanner.vue';
import GenericList from '../GenericList.vue';

export default {
	props: ['site'],
	components: {
		AlertBanner,
		Select,
		GenericList,
	},
	data() {
		return {
			show: true,
			isPhysical: false,
			selectedMigrationMode: '',
			skipFailingPatches: false,
			skipBackups: false,
			scheduledTime: '',
		};
	},
	watch: {},
	resources: {
		migrationOptions() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'get_migration_options',
					};
				},
				initialData: {},
				auto: true,
			};
		},
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		migrationOptions() {
			return this.$resources?.migrationOptions?.data ?? {};
		},
		migrationChoices() {
			return Object.keys(this.migrationOptions)
				.map((e) => ({
					label: e,
					value: e,
				}))
				.filter((e) => !this.migrationOptions[e.value].hidden);
		},
		selectedMigrationChoiceDetails() {
			return this.migrationOptions[this.selectedMigrationMode];
		},
		showSchedulingOption() {
			return this.selectedMigrationChoiceDetails?.allow_scheduling;
		},
		selectedMigrationChoiceOptions() {
			return this.selectedMigrationChoiceDetails?.options || {};
		},
		updatableApps() {
			if (this.selectedMigrationMode !== 'Update Site') return [];

			if (!this.selectedMigrationChoiceOptions.site_update_available) return [];
			let installedApps =
				this.selectedMigrationChoiceOptions.site_update_information.installed_apps.map(
					(d) => d.app,
				);
			return this.selectedMigrationChoiceOptions.site_update_information.apps.filter(
				(app) => installedApps.includes(app.app),
			);
		},
		updateSiteListOptions() {
			return {
				data: this.updatableApps.filter(
					(app) => app.current_hash !== app.next_hash,
				),
				columns: [
					{
						label: 'App',
						fieldname: 'app',
						format(value, row) {
							return row.title || value;
						},
					},
					{
						label: 'Current Version',
						type: 'Badge',
						format(value, row) {
							return row.will_branch_change
								? row.current_branch
								: row.current_tag || row.current_hash.slice(0, 7);
						},
						link(value, row) {
							if (row.will_branch_change) {
								return `${row.repository_url}/tree/${row.current_branch}`;
							}
							if (row.current_tag) {
								return `${row.repository_url}/releases/tag/${row.current_tag}`;
							}
							if (row.current_hash) {
								return `${row.repository_url}/commit/${row.current_hash}`;
							}
						},
					},
					{
						label: 'Next Version',
						type: 'Badge',
						format(value, row) {
							return row.will_branch_change
								? row.branch
								: row.next_tag || row.next_hash.slice(0, 7);
						},
						link(value, row) {
							if (row.will_branch_change) {
								return `${row.repository_url}/tree/${row.branch}`;
							}
							if (row.next_tag) {
								return `${row.repository_url}/releases/tag/${row.next_tag}`;
							}
							if (row.next_hash) {
								return `${row.repository_url}/commit/${row.next_hash}`;
							}
						},
					},
				],
			};
		},
	},
	methods: {
		resetValues() {},
		triggerMigration() {
			// Trigger Migration Logic
		},
	},
};
</script>
