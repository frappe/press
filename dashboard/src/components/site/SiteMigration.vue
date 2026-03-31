<template>
	<!-- This page is named as SiteMigration but the doctype is `Site Action` -->
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
			size: 'xl',
		}"
		v-model="show"
		@close="resetValues"
	>
		<template #body-content>
			<div
				v-if="this.$resources?.migrationOptions?.loading"
				class="flex flex-col items-center justify-center h-[200px]"
			>
				<Spinner class="h-4 w-4 text-gray-600" />
			</div>
			<div v-else class="flex flex-col gap-3">
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

				<!-- Warning -->
				<AlertBanner
					v-if="warningMessage"
					:type="'warning'"
					:title="warningMessage"
					:show-icon="false"
				/>

				<!-- Move Site To Different Server / Bench -->
				<div
					v-if="
						selectedMigrationMode == 'Move Site To Different Server / Bench'
					"
					class="flex flex-col gap-3"
				>
					<!-- Choose Bench Type -->
					<div
						class="flex w-full flex-row gap-2 rounded-md border p-1 text-p-base text-gray-800"
					>
						<div
							class="w-1/2 text-base cursor-pointer rounded-sm py-2 text-center transition-all"
							:class="{
								'bg-gray-100': benchMovementType == 'Create A New Bench',
							}"
							@click="benchMovementType = 'Create A New Bench'"
						>
							New Bench
						</div>
						<div
							class="w-1/2 text-base cursor-pointer rounded-sm py-2 text-center transition-all"
							:class="{
								'bg-gray-100': benchMovementType == 'Move To Existing Bench',
							}"
							@click="benchMovementType = 'Move To Existing Bench'"
						>
							Existing Bench
						</div>
					</div>

					<!-- Choose Release Group (For Existing) -->
					<div
						class="flex flex-col gap-2"
						v-if="benchMovementType == 'Move To Existing Bench'"
					>
						<p class="text-sm text-gray-700">Select Bench</p>
						<FormControl
							type="combobox"
							:options="
								availableReleaseGroups.map((e) => ({
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
							type="combobox"
							:options="
								availableServersForSelectedReleaseGroup.map((e) => ({
									label: e.title ? `${e.title} (${e.name})` : e.name,
									value: e.name,
								}))
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

					<!-- Choose Server Type (For New) -->
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

					<!-- Choose The Server (For New + Dedicated) -->
					<div
						class="flex flex-col gap-2"
						v-if="
							benchMovementType == 'Create A New Bench' &&
							selectedServerType == 'Dedicated Server'
						"
					>
						<p class="text-sm text-gray-700">Select Server</p>
						<FormControl
							type="combobox"
							:options="
								dedicatedServersForNewReleaseGroup.map((e) => ({
									label: e.title ? `${e.title} (${e.name})` : e.name,
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
							type="combobox"
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

						<p
							v-if="!$site.doc.group_public"
							class="mt-1 text-sm text-gray-600"
							:showIcon="false"
						>
							If the region you're looking for isn't available, please follow
							<a
								href="https://docs.frappe.io/cloud/site/site-migrations/move-site-to-different-region"
								target="_blank"
								class="underline"
								>this documentation</a
							>
							to add it.
						</p>
					</div>
				</div>

				<!-- Checkbox  -->
				<Checkbox
					v-if="selectedMigrationMode"
					v-model="skipFailingPatches"
					label="Skip Failing Patches"
					size="sm"
				/>

				<!-- Scheduling Option -->
				<div v-if="showSchedulingOption" class="flex flex-col gap-2">
					<p class="text-sm text-gray-700">Choose Scheduled Time</p>
					<DateTimeControl v-model="scheduledTime" :hideLabel="true" />
				</div>

				<!-- Error Message -->
				<ErrorMessage :message="errorMessage" />
			</div>
		</template>
	</Dialog>
</template>
<script>
import { getCachedDocumentResource, Select, Checkbox } from 'frappe-ui';
import AlertBanner from '../AlertBanner.vue';
import GenericList from '../GenericList.vue';
import FormControl from 'frappe-ui/src/components/FormControl/FormControl.vue';
import { dayjsIST } from '../../utils/dayjs';

export default {
	props: ['site', 'defaultAction', 'defaultNewBenchName'],
	components: {
		AlertBanner,
		Select,
		GenericList,
		Checkbox,
	},
	data() {
		return {
			show: true,
			selectedMigrationMode: '',
			skipFailingPatches: false,
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
				onSuccess: () => {
					this.autoSelectMigrationOption();
				},
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
							group: this.selectedReleaseGroupToMoveTo || null,
							server: this.selectedServerToMoveTo,
							new_group_name: this.selectedReleaseGroupToMoveTo
								? null
								: this.newBenchGroupName,
							skip_failing_patches: this.skipFailingPatches,
							scheduled_time: this.scheduledTimeInIST,
							cluster: this.selectedRegion,
						},
					};
				},
				onSuccess: (result) => {
					if (result?.message) {
						console.log(result.message);
						this.$router.push({
							name: 'Site Migration',
							params: { id: result.message },
						});
					}
					this.hide();
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
				onSuccess: (result) => {
					if (result?.message) {
						this.$router.push({
							name: 'Site Job',
							params: { id: result.message },
						});
					}
					this.hide();
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
				this.$resources?.migrateSite?.error ??
				''
			);
		},
		migrationRequestLoading() {
			return (
				this.$resources?.createMigrationPlan?.loading ||
				this.$resources?.migrateSite?.loading ||
				false
			);
		},
		migrationOptions() {
			return this.$resources?.migrationOptions?.data?.message ?? {};
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
		// Move Site To Different Server / Bench
		availableReleaseGroups() {
			if (
				this.selectedMigrationMode !== 'Move Site To Different Server / Bench'
			)
				return [];
			return (
				this.selectedMigrationChoiceOptions?.available_release_groups ?? []
			);
		},
		availableServersForSelectedReleaseGroup() {
			if (
				this.selectedMigrationMode !== 'Move Site To Different Server / Bench'
			)
				return [];
			if (this.benchMovementType !== 'Move To Existing Bench') return [];
			return (
				this.availableReleaseGroups.find(
					(e) => e.name === this.selectedReleaseGroupToMoveTo,
				)?.servers ?? []
			);
		},
		dedicatedServersForNewReleaseGroup() {
			if (
				this.selectedMigrationMode !== 'Move Site To Different Server / Bench'
			)
				return [];
			if (this.benchMovementType !== 'Create A New Bench') return [];
			if (this.selectedServerType !== 'Dedicated Server') return [];
			return (
				this.selectedMigrationChoiceOptions
					?.dedicated_servers_for_new_release_group ?? []
			);
		},
		availableRegionsToMoveSiteTo() {
			if (this.selectedMigrationMode !== 'Move Site To Different Region')
				return [];
			return this.selectedMigrationChoiceOptions?.available_regions ?? [];
		},
		warningMessage() {
			return {
				'In-Place Migrate Site':
					'Runs `bench migrate` without a backup. Proceed with caution.',
				'Move Site To Different Server / Bench':
					'Site will be unavailable during this process.',
				'Move Site To Different Region':
					'Site will be unavailable during this process.',
			}[this.selectedMigrationMode];
		},
		scheduledTimeInIST() {
			if (!this.scheduledTime) return;
			return dayjsIST(this.scheduledTime).format('YYYY-MM-DDTHH:mm');
		},
	},
	methods: {
		autoSelectMigrationOption() {
			// Check if 'action' is passed via prop or URL params
			const actionFromProp = this.defaultAction;
			const actionFromUrl = this.$route?.query?.action;
			const actionToSelect = actionFromProp || actionFromUrl;

			if (!actionToSelect) return;

			// Check if the action exists in migration choices and is not hidden
			const matchingChoice = this.migrationChoices.find(
				(choice) => choice.value === actionToSelect,
			);

			if (matchingChoice) {
				// Auto-select the option
				this.selectedMigrationMode = actionToSelect;

				// Set default new bench name if provided and not already set
				if (this.defaultNewBenchName && !this.newBenchGroupName) {
					this.newBenchGroupName = this.defaultNewBenchName;
				}
			}
		},
		resetValues(skip_migration_mode_set = false) {
			if (!skip_migration_mode_set) {
				this.selectedMigrationMode = '';
			}
			this.skipFailingPatches = false;
			this.scheduledTime = '';

			// For migration
			this.benchMovementType = 'Create A New Bench';
			this.selectedReleaseGroupToMoveTo = '';
			this.selectedServerToMoveTo = '';
			this.selectedServerType = 'Shared Server';

			// Reset to default bench name if provided, otherwise empty
			this.newBenchGroupName = this.defaultNewBenchName || '';

			// Reset the errors
			if (this.$resources?.createMigrationPlan) {
				this.$resources.createMigrationPlan.error = null;
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
		},
		hide() {
			this.show = false;
			this.$emit('update:modelValue', false);
			this.$emit('close');
		},
	},
};
</script>
