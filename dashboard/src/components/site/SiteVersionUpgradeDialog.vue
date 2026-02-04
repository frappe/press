<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Upgrade Site Version' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<!-- Public bench simple upgrade -->
				<p v-if="$site.doc?.group_public && nextVersion" class="text-base">
					The site <b>{{ $site.doc.host_name }}</b> will be upgraded to
					<b>{{ nextVersion }}</b>
				</p>

				<!-- Private bench upgrade flow -->
				<template v-else-if="!$site.doc?.group_public && nextVersion">
					<!-- If existing compatible bench found -->
					<template
						v-if="upgradeStep === 'ready_to_upgrade' && existingBenchGroup"
					>
						<div class="rounded-lg bg-green-50 p-3 mb-4">
							<div class="text-sm font-medium text-green-800">
								✓ Compatible bench found
							</div>
							<p class="text-sm text-green-700 mt-1">
								Your site will be moved to
								<b>{{ existingBenchGroupTitle }}</b> for
								<b>{{ nextVersion }}</b>
							</p>
						</div>
						<DateTimeControl
							v-model="targetDateTime"
							label="Schedule Time in IST"
						/>
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
					</template>

					<!--  Incompatible apps, cannot upgrade -->
					<template
						v-else-if="
							upgradeStep === 'ready_to_upgrade' &&
							!appCompatibility.can_upgrade
						"
					>
						<div class="rounded-lg bg-red-50 p-3">
							<div class="text-sm font-medium text-red-800 mb-2">
								Migration isn't possible - Incompatible apps:
							</div>
							<ul class="list-inside list-disc text-sm text-red-700">
								<li v-for="app in appCompatibility.incompatible" :key="app.app">
									<b>{{ app.app }}</b
									>: {{ app.reason }}
								</li>
							</ul>
						</div>
					</template>

					<template
						v-else-if="
							upgradeStep === 'ready_to_upgrade' && appCompatibility.can_upgrade
						"
					>
						<div
							v-if="appCompatibility.custom_apps.length === 0"
							class="rounded-lg bg-green-50 p-3 mb-4"
						>
							<div class="text-sm font-medium text-green-800">
								✓ Migration is possible
							</div>
							<p class="text-sm text-green-700 mt-1">
								All apps are compatible with {{ nextVersion }}
							</p>
						</div>
						<!-- Source selection for custom apps-->
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
							<table class="w-full table-fixed">
								<thead>
									<tr class="border-b-2 border-blue-200">
										<th
											class="text-left py-2 px-3 font-medium text-sm text-blue-900 w-1/2"
										>
											App
										</th>
										<th
											class="text-left py-2 px-3 font-medium text-sm text-blue-900 w-1/2"
										>
											Branch *
										</th>
									</tr>
								</thead>
								<tbody>
									<tr
										v-for="app in appCompatibility.custom_apps"
										:key="app.app"
										class="border-b border-blue-100 hover:bg-blue-100 transition-colors"
									>
										<td class="py-3 px-3 w-1/2">
											<div class="font-medium text-sm text-blue-900">
												{{ app.app }}
											</div>
											<div
												class="text-xs text-gray-600 truncate mt-1"
												:title="app.repository_url"
											>
												{{ app.repository_url }}
											</div>
										</td>
										<td class="py-3 px-3 w-1/2">
											<FormControl
												type="combobox"
												:options="
													app.branches.map((b) => ({ label: b, value: b }))
												"
												:modelValue="customAppSources[app.app]?.branch"
												@update:modelValue="
													updateCustomAppSource(app, 'branch', $event)
												"
												placeholder="Select branch..."
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
						<DateTimeControl
							v-model="targetDateTime"
							label="Schedule Time in IST"
							class="mt-4"
						/>
						<div
							v-if="
								!existingBenchGroup && targetDateTime && !isScheduleTimeValid
							"
							class="rounded bg-yellow-50 p-3 mt-2"
						>
							<div class="text-sm text-yellow-800">
								⚠️ When creating a new private bench, schedule time must be at
								least 30 minutes from now to allow for bench deployment.
							</div>
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
					</template>
				</template>

				<div
					v-if="skipBackups"
					class="flex items-center rounded bg-gray-50 p-4 text-sm text-gray-700"
				>
					<lucide-info class="mr-2 h-4 w-8" />
					Backups will not be taken during the upgrade process and in case of
					any failure rollback will not be possible.
				</div>
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
				variant="solid"
				label="Schedule Upgrade"
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
				variant="subtle"
				label="Close"
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
				variant="solid"
				label="Create Bench & Schedule Upgrade"
				:disabled="
					!newReleaseGroupTitle ||
					!hasValidCustomAppSources ||
					!targetDateTime ||
					!isScheduleTimeValid
				"
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
import DateTimeControl from '../DateTimeControl.vue';

export default {
	name: 'SiteVersionUpgradeDialog',
	props: ['site'],
	components: { DateTimeControl },
	data() {
		return {
			show: true,
			targetDateTime: null,
			skipBackups: false,
			skipFailingPatches: false,
			upgradeStep: null, // 'ready_to_upgrade'
			existingBenchGroup: null,
			existingBenchGroupTitle: null,
			appCompatibility: {
				compatible: [],
				incompatible: [],
				custom_apps: [],
				can_upgrade: false,
			},
			newReleaseGroupTitle: '',
			customAppSources: {}, // { app_name: { branch, source } }
			createdBenchDetails: null, // { release_group, bench, deploy_job }
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
			// Check if all custom apps have a valid branch selected
			return this.appCompatibility.custom_apps.every((app) => {
				const branch = this.customAppSources[app.app]?.branch;
				if (!branch) return false;
				if (Array.isArray(app.branches) && app.branches.length) {
					return app.branches.includes(branch);
				}
				return true;
			});
		},
		minimumScheduleTime() {
			if (!this.existingBenchGroup && this.appCompatibility.can_upgrade) {
				const now = new Date();
				const minTime = new Date(now.getTime() + 30 * 60 * 1000);
				return this.$dayjs(minTime).format('YYYY-MM-DDTHH:mm');
			}
			return null;
		},
		isScheduleTimeValid() {
			// Validate schedule time is at least 30 mins from now when creating new bench
			if (!this.targetDateTime) return true;
			if (!this.existingBenchGroup) {
				const scheduledTime = this.$dayjs(this.targetDateTime);
				const minimumTime = this.$dayjs().add(30, 'minute');
				return (
					scheduledTime.isAfter(minimumTime) ||
					scheduledTime.isSame(minimumTime)
				);
			}
			return true;
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
					// Redirect to bench group deploy page
					// const deployPage = `/groups/${destination_group}`;
					// this.$router.push(deployPage);
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
				onSuccess: async (result) => {
					if (result.exists) {
						// Existing bench found
						this.existingBenchGroup = result.release_group;
						const titleResult = await frappe.db.get_value(
							'Release Group',
							result.release_group,
							'title',
						);
						this.existingBenchGroupTitle =
							titleResult.message?.title || result.release_group;
						this.upgradeStep = 'ready_to_upgrade';
					} else {
						// No existing bench - check app compatibility
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
				onSuccess: (compatibility) => {
					this.appCompatibility = compatibility;
					this.upgradeStep = 'ready_to_upgrade';

					if (!compatibility.can_upgrade) {
						// Incompatible public apps
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
						description: `Version upgrade will be scheduled automatically after successful deployment.`,
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
				compatible: [],
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
