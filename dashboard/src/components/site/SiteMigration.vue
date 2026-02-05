<template>
	<Dialog
		:options="{
			title: 'Migrate Site',
			actions: selectedMigrationMode
				? [
						{
							label: selectedMigrationChoiceDetails?.button_label || 'Proceed',
							disabled: migrationRequestLoading,
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
				<!-- <p v-if="selectedMigrationMode" class="text-base text-gray-700 mb-2">
					{{ selectedMigrationChoiceDetails?.description }}
				</p> -->
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

				<!-- Move Site To Different Server -->
				<div
					v-else-if="selectedMigrationMode == 'Move Site To Different Server'"
					class="flex flex-col gap-3"
				>
					<!-- Chose The Server -->
					<div class="flex flex-col gap-2">
						<p class="text-sm text-gray-700">Select Server</p>
						<FormControl
							type="select"
							:options="
								dedicatedServersToMoveSiteTo.map((e) => ({
									label: e.title,
									value: e.name,
								}))
							"
							size="md"
							variant="outline"
							placeholder="Select Server"
							v-model="selectedServerToMoveTo"
							required
						/>
					</div>
				</div>

				<!-- Move Site to Different Region -->
				<div
					v-else-if="selectedMigrationMode === 'Move Site To Different Region'"
					class="flex flex-col gap-3"
				>
					<!-- Chose The Region -->
					<div class="flex flex-col gap-2">
						<p class="text-sm text-gray-700">Select Region</p>
						<FormControl
							type="select"
							:options="
								availableRegionsToMoveSiteTo.map((e) => ({
									label: e.title,
									value: e.name,
								}))
							"
							size="md"
							variant="outline"
							placeholder="Select Region"
							v-model="selectedRegion"
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

				<!-- Error Message -->
				<ErrorMessage :message="errorMessage" />
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
			selectedRegion: '',
		};
	},
	watch: {
		selectedMigrationMode() {
			this.resetValues(true);
		},
	},
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
		createMigrationPlan() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'create_migration_plan',
						args: {
							type: this.selectedMigrationMode,
							group: this.selectedReleaseGroupToMoveTo,
							server: this.selectedServerToMoveTo,
							new_group_name: this.newBenchGroupName,
							skip_failing_patches: this.skipFailingPatches,
							skip_backups: false,
							scheduled_time: this.scheduledTime,
							cluster: this.selectedRegion,
						},
					};
				},
			};
		},
		changeRegion() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'change_region',
						args: {
							cluster: this.selectedRegion,
							scheduled_time: this.scheduledTime,
							skip_failing_patches: this.skipFailingPatches,
						},
					};
				},
			};
		},
		migrateSite() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'migrate',
						args: {
							skip_failing_patches: this.skipFailingPatches,
						},
					};
				},
			};
		},
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		errorMessage() {
			return (
				this.$resources?.createMigrationPlan?.error ??
				this.$resources?.changeRegion?.error ??
				this.$resources?.migrateSite?.error ??
				''
			);
		},
		migrationRequestLoading() {
			return (
				this.$resources?.createMigrationPlan?.loading ||
				this.$resources?.changeRegion?.loading ||
				this.$resources?.migrateSite?.loading ||
				false
			);
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
		dedicatedServersToMoveSiteTo() {
			if (this.selectedMigrationMode !== 'Move Site To Different Server')
				return [];
			return this.selectedMigrationChoiceOptions?.dedicated_servers ?? [];
		},
		availableRegionsToMoveSiteTo() {
			if (this.selectedMigrationMode !== 'Move Site To Different Region')
				return [];
			return this.selectedMigrationChoiceOptions?.available_regions ?? [];
		},
	},
	methods: {
		resetValues(skip_migration_mode_set = false) {
			if (!skip_migration_mode_set) {
				this.selectedMigrationMode = '';
			}
			this.skipFailingPatches = false;
			this.skipBackups = false;
			this.scheduledTime = '';

			// For migration
			this.benchMovementType = 'Create A New Bench';
			this.selectedReleaseGroupToMoveTo = '';
			this.selectedServerToMoveTo = '';
			this.selectedServerType = 'Shared Server';

			this.newBenchGroupName = '';

			// Reset the errors
			if (this.$resources?.createMigrationPlan) {
				this.$resources.createMigrationPlan.error = null;
			}
			if (this.$resources?.changeRegion) {
				this.$resources.changeRegion.error = null;
			}
			if (this.$resources?.migrateSite) {
				this.$resources.migrateSite.error = null;
			}
		},
		triggerMigration() {
			if (this.selectedMigrationMode === 'In-Place Migrate Site') {
				this.$resources?.migrateSite?.submit();
			} else {
				this.$resources?.createMigrationPlan?.submit();
			}

			// this.show = false;
			// this.$emit('update:modelValue', false);
			// this.$emit('close');
		},
	},
};
</script>
