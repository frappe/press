<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Upgrade Site Version' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<!-- Public bench upgrade -->
				<p v-if="$site.doc?.group_public && nextVersion" class="text-base">
					The site <b>{{ $site.doc.host_name }}</b> will be upgraded to
					<b>{{ nextVersion }}</b>
				</p>

				<!-- Private bench upgrade -->
				<div v-else-if="!$site.doc?.group_public && nextVersion">
					<!-- If existing compatible bench found  -->
					<div v-if="upgradeStep === 'ready_to_upgrade' && existingBenchGroup">
						<div class="mb-4 text-base">
							<p>
								The site <b>{{ $site.doc.host_name }}</b> will be moved to
								<b>{{ existingBenchGroupTitle }}</b> bench group for upgrade to
								{{ nextVersion }}.
							</p>
						</div>
						<div class="mt-4">
							<span class="text-xs text-ink-gray-5 mb-2"
								>Schedule Time in IST</span
							>
							<DateTimePicker v-model="targetDateTime" />
						</div>
						<FormControl
							label="Skip failing patches if any"
							type="checkbox"
							v-model="skipFailingPatches"
						/>
						<FormControl
							label="Skip backups"
							type="checkbox"
							v-model="skipBackups"
							class="ml-4"
						/>
					</div>

					<AlertBanner
						v-else-if="
							upgradeStep === 'ready_to_upgrade' &&
							!appCompatibility.can_upgrade
						"
						:title="`Migration isn't possible due to incompatible app(s): <b>${appCompatibility.incompatible.join(', ')}</b>`"
						type="error"
					/>

					<div
						v-else-if="
							upgradeStep === 'ready_to_upgrade' && appCompatibility.can_upgrade
						"
					>
						<div
							v-if="appCompatibility.custom_apps.length === 0"
							class="mb-4 text-base"
						>
							<p>
								The site <b>{{ $site.doc.host_name }}</b> will be moved to a new
								<b>{{ nextVersion }}</b> bench group for upgrade.
							</p>
						</div>
						<div
							v-else-if="
								appCompatibility.custom_apps &&
								appCompatibility.custom_apps.length > 0
							"
							class="space-y-3 mt-4"
						>
							<div class="text-sm font-medium text-gray-700 mb-3">
								Select Branch for Custom Apps
							</div>
							<table class="w-full table-fixed pb-4 border-b border-gray-100">
								<thead>
									<tr class="text-sm text-gray-600">
										<th class="font-medium text-left py-2 w-3/5">App</th>
										<th class="font-medium text-left py-2 w-2/5">Branch *</th>
									</tr>
								</thead>
								<tbody>
									<tr
										v-for="app in appCompatibility.custom_apps"
										:key="app.app"
										class="hover:bg-gray-100 transition-colors"
									>
										<td class="py-3 w-3/5">
											<div class="font-medium text-sm">
												{{ app.title }}
											</div>
											<div
												class="text-xs text-gray-600 truncate mt-1"
												:title="app.repository_url"
											>
												{{ app.repository_url }}
											</div>
										</td>
										<td class="py-3 w-2/5">
											<FormControl
												type="combobox"
												:options="
													app.branches.map((b) => ({ label: b, value: b }))
												"
												:modelValue="customAppSources[app.app]?.branch"
												@update:modelValue="
													updateCustomAppSource(app, 'branch', $event)
												"
												placeholder="Select branch"
											/>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
						<FormControl
							v-if="!existingBenchGroup"
							label="Release Group Title"
							type="text"
							v-model="newReleaseGroupTitle"
							placeholder="e.g., My Team - Version 15"
							class="mt-4"
						/>
						<div class="mt-4">
							<span class="text-xs text-ink-gray-5 mb-2"
								>Schedule Time in IST</span
							>
							<DateTimePicker v-model="targetDateTime" />
						</div>
						<AlertBanner
							v-if="
								!existingBenchGroup && targetDateTime && !isScheduleTimeValid
							"
							title="Schedule time must be at least 30 minutes from now to allow for bench deployment."
							type="warning"
						>
						</AlertBanner>
						<FormControl
							label="Skip failing patches if any"
							type="checkbox"
							v-model="skipFailingPatches"
						/>
						<FormControl
							label="Skip backups"
							type="checkbox"
							v-model="skipBackups"
							class="ml-4"
						/>
					</div>
				</div>
				<AlertBanner
					v-if="skipBackups"
					title="Backups will not be taken during the upgrade process and in case of
					any failure rollback will not be possible."
					type="warning"
				></AlertBanner>
				<p v-if="message && !errorMessage" class="text-sm text-gray-700">
					{{ message }}
				</p>
				<ErrorMessage :message="errorMessage" />
			</div>
		</template>

		<template v-if="$site.doc?.group_public || upgradeStep" #actions>
			<!-- Public bench upgrade -->
			<Button
				v-if="$site.doc?.group_public && nextVersion"
				class="w-full"
				variant="solid"
				label="Upgrade"
				:loading="$resources.versionUpgrade.loading"
				@click="$resources.versionUpgrade.submit()"
			/>
			<!-- Existing bench - Schedule upgrade -->
			<Button
				v-if="
					!$site.doc?.group_public &&
					upgradeStep === 'ready_to_upgrade' &&
					existingBenchGroup
				"
				class="w-full"
				:class="skipBackups ? 'text-white bg-red-600 hover:bg-red-700' : ''"
				variant="solid"
				:label="targetDateTime ? 'Schedule Upgrade' : 'Upgrade Now'"
				:loading="$resources.versionUpgrade.loading"
				@click="handleUpgradeSubmit"
			/>
			<!-- Incompatible apps - close dialog-->
			<Button
				v-if="
					!$site.doc?.group_public &&
					upgradeStep === 'ready_to_upgrade' &&
					!existingBenchGroup &&
					!appCompatibility.can_upgrade
				"
				class="w-full"
				:class="skipBackups ? 'text-white bg-red-600 hover:bg-red-700' : ''"
				variant="subtle"
				:label="targetDateTime ? 'Schedule Upgrade' : 'Upgrade Now'"
				@click="show = false"
			/>
			<!-- Create bench and upgrade -->
			<Button
				v-if="
					!$site.doc?.group_public &&
					upgradeStep === 'ready_to_upgrade' &&
					!existingBenchGroup &&
					appCompatibility.can_upgrade
				"
				class="w-full"
				:class="skipBackups ? 'text-white bg-red-600 hover:bg-red-700' : ''"
				variant="solid"
				:label="
					targetDateTime
						? 'Deploy Bench & Schedule Upgrade'
						: 'Deploy Bench & Upgrade Site Now'
				"
				:disabled="disableButton"
				:loading="
					$resources.versionUpgrade.loading ||
					$resources.createPrivateBench.loading
				"
				@click="handleUpgradeSubmit"
			/>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import AlertBanner from '../AlertBanner.vue';
import DateTimePicker from 'frappe-ui/src/components/DatePicker/DateTimePicker.vue';

export default {
	name: 'SiteVersionUpgradeDialog',
	props: ['site'],
	components: { DateTimePicker, AlertBanner },
	data() {
		return {
			show: true,
			targetDateTime: null,
			skipBackups: false,
			skipFailingPatches: false,
			upgradeStep: null,
			existingBenchGroup: null,
			existingBenchGroupTitle: null,
			appCompatibility: {
				incompatible: [],
				custom_apps: [],
				can_upgrade: false,
			},
			newReleaseGroupTitle: '',
			customAppSources: {}, // { app_name: { branch, source } }
			createdBenchDetails: null,
		};
	},

	computed: {
		nextVersion() {
			const nextNumber = Number(this.$site.doc?.version.split(' ')[1]);
			if (
				isNaN(nextNumber) ||
				this.$site.doc?.version === this.$site.doc?.latest_frappe_version
			)
				return null;

			return `Version ${nextNumber + 1}`;
		},
		message() {
			if (this.$site.doc?.version === this.$site.doc?.latest_frappe_version) {
				return 'This site is already on the latest version.';
			} else if (this.$site.doc?.version === 'Nightly') {
				return "This site is on a nightly version and doesn't need to be upgraded.";
			}
			return '';
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime).format(
				'YYYY-MM-DDTHH:mm',
			);

			return datetimeInIST;
		},
		errorMessage() {
			return (
				this.$resources.versionUpgrade.error ||
				this.$resources.checkExistingBench.error ||
				this.$resources.checkAppCompatibility.error ||
				this.$resources.createPrivateBench.error
			);
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		hasValidCustomAppSources() {
			return this.appCompatibility.custom_apps.every((app) => {
				const branch = this.customAppSources[app.app]?.branch;
				if (!branch) return false;
				if (Array.isArray(app.branches) && app.branches.length) {
					return app.branches.includes(branch);
				}
				return true;
			});
		},
		isScheduleTimeValid() {
			// Atleast 30 mins from now for deploying bench
			if (!this.targetDateTime) return true;
			if (!this.existingBenchGroup) {
				const scheduledTime = this.targetDateTime.$d
					? this.$dayjs(this.targetDateTime.$d)
					: this.$dayjs(this.targetDateTime);
				const minimumTime = this.$dayjs().add(30, 'minute');
				return scheduledTime.isAfter(minimumTime);
			}
			return true;
		},
		disableButton() {
			if (!this.newReleaseGroupTitle || !this.hasValidCustomAppSources) {
				return true;
			}
			if (this.targetDateTime && !this.isScheduleTimeValid) {
				return true;
			}
		},
	},
	resources: {
		versionUpgrade() {
			const destination_group =
				this.createdBenchDetails?.release_group || this.existingBenchGroup;
			return {
				url: 'press.api.site.version_upgrade',
				params: {
					name: this.site,
					destination_group: destination_group,
					skip_failing_patches: this.skipFailingPatches,
					skip_backups: this.skipBackups,
					scheduled_datetime: this.datetimeInIST,
				},
				onSuccess: (data) => {
					toast.success("Site's version upgrade has been scheduled.");
					this.show = false;
				},
			};
		},
		checkExistingBench() {
			return {
				url: 'press.api.site.check_existing_upgrade_bench',
				params: {
					name: this.site,
					version: this.$site.doc?.version,
				},
				auto: !this.$site.doc?.group_public,
				onSuccess: (data) => {
					if (data.exists) {
						this.existingBenchGroup = data.release_group;
						this.existingBenchGroupTitle = data.release_group_title;
						this.upgradeStep = 'ready_to_upgrade';
					} else {
						this.$resources.checkAppCompatibility.fetch();
					}
				},
			};
		},
		checkAppCompatibility() {
			return {
				url: 'press.api.site.check_app_compatibility_for_upgrade',
				params: {
					name: this.site,
					version: this.$site.doc?.version,
				},
				onSuccess: (data) => {
					this.appCompatibility = data;
					this.upgradeStep = 'ready_to_upgrade';

					if (!data.can_upgrade) {
						toast.error('Migration blocked - incompatible apps found');
					}
				},
			};
		},
		createPrivateBench() {
			const custom_app_sources = this.appCompatibility.custom_apps.map(
				(app) => ({
					app: app.app,
					branch: this.customAppSources[app.app]?.branch || app.branch,
					repository_url: app.repository_url,
					github_installation_id: app.github_installation_id,
				}),
			);

			return {
				url: 'press.api.site.create_private_bench_for_upgrade',
				params: {
					name: this.site,
					version: this.$site.doc?.version,
					release_group_title: this.newReleaseGroupTitle,
					custom_app_sources: custom_app_sources,
				},
				onSuccess(data) {
					this.resetValues();
					this.show = false;
					this.$router.push({
						name: 'Release Group Detail',
						params: {
							name: data,
						},
					});
				},
			};
		},
	},
	methods: {
		updateCustomAppSource(app, field, value) {
			const appName = app.app;
			if (!this.customAppSources[appName]) {
				this.customAppSources[appName] = { branch: '' };
			}
			this.customAppSources[appName][field] = value;
		},
		async handleUpgradeSubmit() {
			if (this.existingBenchGroup) {
				// Upgrade to existing bench
				this.$resources.versionUpgrade.submit();
			} else {
				// handle new bench deploy
				const custom_app_sources = this.appCompatibility.custom_apps.map(
					(app) => ({
						app: app.app,
						branch: this.customAppSources[app.app]?.branch || app.branch,
						repository_url: app.repository_url,
						github_installation_id: app.github_installation_id,
					}),
				);

				try {
					const benchData = await this.$resources.createPrivateBench.fetch({
						name: this.site,
						version: this.$site.doc?.version,
						release_group_title: this.newReleaseGroupTitle,
						custom_app_sources: custom_app_sources,
						scheduled_time: this.datetimeInIST,
						skip_failing_patches: this.skipFailingPatches,
						skip_backups: this.skipBackups,
					});

					this.createdBenchDetails = benchData;
					toast.success('New bench deployment started', {
						description: `Site app versions will be upgraded after successful deployment.`,
					});
					this.show = false;
				} catch (error) {
					toast.error('Failed to create bench');
					console.error(error);
				}
			}
		},
		resetValues() {
			this.targetDateTime = null;
			this.skipBackups = false;
			this.skipFailingPatches = false;
			this.upgradeStep = null;
			this.existingBenchGroup = null;
			this.existingBenchGroupTitle = null;
			this.appCompatibility = {
				incompatible: [],
				custom_apps: [],
				can_upgrade: false,
			};
			this.newReleaseGroupTitle = '';
			this.customAppSources = {};
			this.createdBenchDetails = null;
		},
	},
};
</script>
