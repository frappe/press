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
				<!-- Move From Shared To Private Bench -->
				<div
					v-else-if="
						selectedMigrationMode == 'Move From Shared To Private Bench'
					"
					class="flex flex-col gap-3"
				>
					<!-- Chose Bench Related Opinion -->
					<div class="flex flex-col gap-2">
						<p class="text-sm text-gray-700">Select Movement Type</p>
						<FormControl
							type="select"
							:options="[
								{
									label: 'Move To Existing Bench',
									value: 'Move To Existing Bench',
								},
								{
									label: 'Create A New Bench',
									value: 'Create A New Bench',
								},
							]"
							size="md"
							variant="outline"
							placeholder="Select Movement Type"
							v-model="benchMovementType"
							required
						/>
					</div>
					<!-- Choose Release Group (For Existing) -->
					<div
						class="flex flex-col gap-2"
						v-if="benchMovementType == 'Move To Existing Bench'"
					>
						<p class="text-sm text-gray-700">Select Bench Group</p>
						<FormControl
							type="select"
							:options="
								availableReleaseGroupsForMovingToPrivateBench.map((e) => ({
									label: e.title,
									value: e.name,
								}))
							"
							size="md"
							variant="outline"
							placeholder="Choose Release Group"
							v-model="selectedReleaseGroupToMoveTo"
							required
						/>
					</div>
					<!-- Choose Server (For Existing) -->
					<!-- Because, Release group can have multiple server -->
					<div
						class="flex flex-col gap-2"
						v-if="
							benchMovementType == 'Move To Existing Bench' &&
							selectedReleaseGroupToMoveTo
						"
					>
						<p class="text-sm text-gray-700">Select Server</p>
						<FormControl
							type="select"
							:options="
								availableServersForSelectedReleaseGroupForMovingToPrivateBench.map(
									(e) => ({ label: e.title, value: e.name }),
								)
							"
							size="md"
							variant="outline"
							placeholder="Choose Server"
							v-model="selectedServerToMoveTo"
							required
						/>
					</div>

					<!-- New Bench Group Name (For New) -->
					<div
						class="flex flex-col gap-2"
						v-if="benchMovementType == 'Create A New Bench'"
					>
						<p class="text-sm text-gray-700">Provide New Bench Name</p>
						<FormControl
							type="text"
							size="md"
							variant="outline"
							placeholder="Provide New Bench Name"
							v-model="newBenchGroupName"
							required
						/>
					</div>

					<!-- Chose Server Type (For New) -->
					<div
						class="flex flex-col gap-2"
						v-if="benchMovementType == 'Create A New Bench'"
					>
						<p class="text-sm text-gray-700">Select Server Type</p>
						<FormControl
							type="select"
							:options="[
								{
									label: 'Shared Server',
									value: 'Shared Server',
								},
								{
									label: 'Dedicated Server',
									value: 'Dedicated Server',
								},
							]"
							size="md"
							variant="outline"
							placeholder="Select Server Type"
							v-model="selectedServerType"
							required
						/>
					</div>

					<!-- Chose The Server -->
					<div
						class="flex flex-col gap-2"
						v-if="
							benchMovementType == 'Create A New Bench' &&
							selectedServerType == 'Dedicated Server'
						"
					>
						<p class="text-sm text-gray-700">Select Server</p>
						<FormControl
							type="select"
							:options="
								dedicatedServersForNewReleaseGroupForMovingToPrivateBench.map(
									(e) => ({ label: e.title, value: e.name }),
								)
							"
							size="md"
							variant="outline"
							placeholder="Select Server"
							v-model="selectedServerToMoveTo"
							required
						/>
					</div>
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
import FormControl from 'frappe-ui/src/components/FormControl/FormControl.vue';

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

			// For migration
			benchMovementType: 'Create A New Bench',
			selectedReleaseGroupToMoveTo: '',
			selectedServerToMoveTo: '',
			selectedServerType: 'Shared Server',

			newBenchGroupName: '',
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
		// Move Site From Shared Bench to Private Bench
		availableReleaseGroupsForMovingToPrivateBench() {
			if (this.selectedMigrationMode !== 'Move From Shared To Private Bench')
				return {};
			return (
				this.selectedMigrationChoiceOptions?.available_release_groups ?? {}
			);
		},
		availableServersForSelectedReleaseGroupForMovingToPrivateBench() {
			if (this.selectedMigrationMode !== 'Move From Shared To Private Bench')
				return [];
			if (this.benchMovementType !== 'Move To Existing Bench') return [];
			return (
				this.availableReleaseGroupsForMovingToPrivateBench.find(
					(e) => e.name === this.selectedReleaseGroupToMoveTo,
				)?.servers ?? []
			);
		},
		dedicatedServersForNewReleaseGroupForMovingToPrivateBench() {
			if (this.selectedMigrationMode !== 'Move From Shared To Private Bench')
				return [];
			if (this.benchMovementType !== 'Create A New Bench') return [];
			if (this.selectedServerType !== 'Dedicated Server') return [];
			return (
				this.selectedMigrationChoiceOptions
					?.dedicated_servers_for_new_release_group ?? []
			);
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
