<template>
	<Dialog
		v-model="show"
		:options="{
			size: '4xl',
			title: lastDeploy ? 'Update Bench Group' : 'Deploy Bench Group',
		}"
	>
		<template #body-content>
			<AlertBanner
				v-if="benchDocResource.doc.are_builds_suspended"
				class="mb-4"
				title="<b>Builds Suspended:</b> updates will be scheduled to run when builds resume."
				type="warning"
			/>
			<AlertBanner
				v-if="
					benchDocResource.doc.deploy_information.apps.some((app) =>
						app.releases.some((release) => release.is_yanked),
					)
				"
				class="mb-4"
				title="<b>A few commits have been yanked</b>"
				type="info"
			/>
			<!-- Update Steps -->
			<div class="space-y-4">
				<!-- Select Apps Step -->
				<div v-if="step === 'select-apps'">
					<h2 class="mb-4 text-lg font-medium">
						{{ lastDeploy ? 'Select apps to update' : 'Deploy Apps' }}
					</h2>
					<GenericList
						class="max-h-[500px]"
						v-if="benchDocResource.doc.deploy_information.update_available"
						:options="updatableAppOptions"
						@update:selections="handleAppSelection"
					/>
					<p v-else class="text-center text-base text-gray-600">
						No apps to update
					</p>
				</div>

				<!-- Remove Apps Step -->
				<div v-else-if="step === 'removed-apps'">
					<h2 class="mb-4 text-lg font-medium">These apps will be removed</h2>
					<GenericList class="max-h-[500px]" :options="removedAppOptions" />
				</div>

				<!-- Select Site Step -->
				<div v-else-if="step === 'select-sites'">
					<h2 class="mb-4 text-lg font-medium">Select sites to update</h2>
					<GenericList
						class="max-h-[500px]"
						v-if="benchDocResource.doc.deploy_information.sites.length"
						:options="siteOptions"
						@update:selections="handleSiteSelection"
					/>
					<p
						class="text-center text-base font-medium text-gray-600"
						v-else-if="!benchDocResource.doc.deploy_information.sites.length"
					>
						No active sites to update
					</p>
				</div>

				<!-- Restrict Build Step -->
				<div
					v-else-if="step === 'restrict-build' && restrictMessage"
					class="flex flex-col gap-4"
				>
					<div class="flex items-center gap-2">
						<h2 class="text-lg font-medium">Build might fail</h2>
						<a
							href="https://docs.frappe.io/cloud/common-issues/build-might-fail"
							target="_blank"
							class="cursor-pointer rounded-full border border-gray-200 bg-gray-100 p-0.5 text-base text-gray-700"
						>
							<lucide-help-circle :class="`h-4 w-4 text-red-600`" />
						</a>
					</div>
					<p
						class="text-base font-medium text-gray-800"
						v-html="restrictMessage"
					></p>
					<div class="mt-4">
						<FormControl
							label="I understand, run deploy anyway"
							type="checkbox"
							v-model="ignoreWillFailCheck"
						/>
					</div>
				</div>

				<div v-if="canUpdateInPlace" class="flex gap-2">
					<FormControl
						label="Use in place update"
						type="checkbox"
						v-model="useInPlaceUpdate"
					/>
					<Tooltip text="View documentation">
						<a
							href="https://docs.frappe.io/cloud/in-place-updates"
							target="_blank"
						>
							<lucide-help-circle :class="`h-4 w-4 text-gray-600`" />
						</a>
					</Tooltip>
				</div>

				<ErrorMessage :message="errorMessage" />
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-between space-y-2">
				<div v-if="!canShowBack"><!-- Spacer div --></div>
				<Button v-if="canShowBack" label="Back" @click="back" />
				<Button v-if="canShowNext" variant="solid" label="Next" @click="next" />
				<Button
					v-if="canShowDeploy"
					variant="solid"
					:label="deployLabel"
					:loading="
						$resources.deployAndUpdate.loading ||
						$resources.updateInPlace.loading
					"
					@click="updateBench"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { h } from 'vue';
import { Checkbox, getCachedDocumentResource } from 'frappe-ui';
import CommitChooser from '@/components/utils/CommitChooser.vue';
import CommitTag from '@/components/utils/CommitTag.vue';
import GenericList from '../../components/GenericList.vue';
import { getTeam } from '../../data/team';
import { DashboardError } from '../../utils/error';
import AlertBanner from '../AlertBanner.vue';

export default {
	name: 'UpdateReleaseGroupDialog',
	props: ['bench', 'lastDeploy'],
	components: {
		GenericList,
		CommitChooser,
		CommitTag,
		AlertBanner,
	},
	data() {
		return {
			show: true,
			step: '',
			errorMessage: '',
			ignoreWillFailCheck: false,
			useInPlaceUpdate: false,
			restrictMessage: '',
			selectedApps: [],
			selectedSites: [],
		};
	},
	mounted() {
		if (this.hasUpdateAvailable) {
			this.step = 'select-apps';
			if (!this.lastDeploy) {
				// Preselect all updatable apps for first time deploys
				this.handleAppSelection(
					this.benchDocResource.doc?.deploy_information?.apps?.map(
						(app) => app.name,
					) || [],
				);
			}
		} else if (this.hasRemovedApps) {
			this.step = 'removed-apps';
		} else {
			this.step = 'select-sites';
		}
	},
	computed: {
		updatableAppOptions() {
			let deployInformation = this.benchDocResource.doc.deploy_information;
			let appData = deployInformation.apps;

			// preserving this for use in component functions
			const vm = this;

			return {
				data: appData,
				selectable: !!this.lastDeploy,
				columns: [
					{
						label: 'App',
						fieldname: 'title',
						width: 1.75,
					},
					{
						label: 'From',
						fieldname: 'current_hash',
						type: 'Component',
						component({ row: app }) {
							if (!app.current_hash) return null;
							let tag = app.will_branch_change
								? app.current_branch
								: app.current_hash.slice(0, 7);

							return h(CommitTag, {
								tag: tag,
								link: `${app.repository_url}/commit/${tag}`,
							});
						},
					},
					{
						label: 'To',
						fieldname: 'next_release',
						type: 'Component',
						component({ row: app }) {
							if (app.will_branch_change) {
								return h(CommitTag, {
									tag: app.branch,
									link: `${app.repository_url}/commit/${app.branch}`,
								});
							}

							function commitChooserOptions(app) {
								return app.releases.map((release) => {
									const messageMaxLength = 75;
									let message = release.message.split('\n')[0];
									message =
										message.length > messageMaxLength
											? message.slice(0, messageMaxLength) + '...'
											: message;

									return {
										label: release.tag
											? release.tag
											: `${release.hash.slice(0, 7)} - ${message}`,
										value: release.name,
										timestamp: release.timestamp,
										is_yanked: release.is_yanked,
									};
								});
							}

							function initialDeployTo(app) {
								const next_release = app.releases.filter(
									(release) =>
										release.name === app.next_release && !release.is_yanked,
								)[0];

								if (app.will_branch_change) {
									return app.branch;
								} else if (next_release) {
									return next_release.tag || next_release.hash.slice(0, 7);
								} else if (app.next_release_hash) {
									return app.next_release_hash.slice(0, 7);
								} else {
									return null;
								}
							}

							if (!app.releases.length) return undefined;
							let initialValue = {
								label: initialDeployTo(app),
								value:
									app.releases.find(
										(release) =>
											release.name === app.next_release && !release.is_yanked,
									)?.name || null, // Don't make any implicit selections
							};

							return h(CommitChooser, {
								options: commitChooserOptions(app),
								app: app.name,
								source: app.source,
								currentRelease: app.current_release,
								modelValue: initialValue,
								'onUpdate:modelValue': (value) => {
									vm.updateNextRelease(app.name, value.value, value.hash);
								},
							});
						},
					},
					{
						label: 'Status',
						fieldname: 'title',
						type: 'Badge',
						format(value, row) {
							if (
								deployInformation.removed_apps.find(
									(app) => app.name === row.name,
								)
							) {
								return 'Will be Uninstalled';
							} else if (!row.will_branch_change && !row.current_hash) {
								return 'First Deploy';
							}
							return 'Update Available';
						},
					},
					{
						label: 'Changes',
						type: 'Button',
						width: 0.5,
						align: 'right',
						Button({ row }) {
							let url;
							if (row.current_hash && row.next_release) {
								let hash =
									row.releases.find(
										(release) => release.name === row.next_release,
									)?.hash ?? row.next_release_hash;

								if (hash)
									url = `${row.repository_url}/compare/${row.current_hash}...${hash}`;
							} else if (row.next_release) {
								url = `${row.repository_url}/commit/${
									row.releases.find(
										(release) => release.name === row.next_release,
									)?.hash ?? row.next_release_hash
								}`;
							}

							if (!url) return null;

							return {
								label: 'View',
								variant: 'ghost',
								onClick() {
									window.open(url, '_blank');
								},
							};
						},
					},
				],
			};
		},
		removedAppOptions() {
			let deployInformation = this.benchDocResource.doc.deploy_information;
			let appData = deployInformation.removed_apps;

			return {
				data: appData,
				columns: [
					{
						label: 'App',
						fieldname: 'title',
					},
					{
						label: 'Status',
						fieldname: 'name',
						type: 'Badge',
						format() {
							return 'Will be Uninstalled';
						},
					},
				],
			};
		},
		siteOptions() {
			let deployInformation = this.benchDocResource.doc.deploy_information;
			let siteData = deployInformation.sites;
			let team = getTeam();

			/**
			 * If In Place update is being used failed patches are skipped
			 * and site backups are not taken by default.
			 */
			const disabled = this.useInPlaceUpdate;

			return {
				data: siteData,
				selectable: true,
				columns: [
					{
						label: 'Site',
						fieldname: 'name',
					},
					{
						label: 'Skip failed patches',
						fieldname: 'skip_failing_patches',
						width: 0.5,
						type: 'Component',
						component({ row }) {
							return h(Checkbox, {
								modelValue: row.skip_failing_patches,
								disabled,
								'onUpdate:modelValue': (val) => {
									row.skip_failing_patches = val;
								},
							});
						},
					},
					{
						label: 'Skip backup',
						fieldname: 'skip_backups',
						width: 0.3,
						type: 'Component',
						condition() {
							return !!team.doc.skip_backups;
						},
						component({ row }) {
							return h(Checkbox, {
								modelValue: row.skip_backups,
								disabled,
								'onUpdate:modelValue': (val) => {
									row.skip_backups = val;
								},
							});
						},
					},
				],
			};
		},
		benchDocResource() {
			return getCachedDocumentResource('Release Group', this.bench);
		},
		hasUpdateAvailable() {
			return this.benchDocResource.doc.deploy_information.apps.some(
				(app) => app.update_available === true,
			);
		},
		hasRemovedApps() {
			return !!this.benchDocResource.doc.deploy_information.removed_apps.length;
		},
		deployInformation() {
			return this.benchDocResource?.doc.deploy_information;
		},
		canShowBack() {
			if (this.step === 'select-apps') {
				return false;
			}

			return this.hasUpdateAvailable || this.step === 'restrict-build';
		},
		canShowNext() {
			if (this.step === 'select-apps' && !this.lastDeploy) {
				return false;
			}

			if (this.step === 'restrict-build') {
				return false;
			}

			if (this.step === 'select-sites' && !this.restrictMessage) {
				return false;
			}

			return true;
		},
		canShowDeploy() {
			return !this.canShowNext;
		},
		deployLabel() {
			if (!this.lastDeploy) {
				return 'Deploy now';
			}

			if (this.selectedSites.length === 0) {
				return 'Skip and Deploy';
			}

			let site = 'site';
			if (this.selectedSites.length > 1) {
				site = `${this.selectedSites.length} sites`;
			}

			if (this.useInPlaceUpdate) {
				return `Update ${site} in place`;
			}

			return `Deploy and update ${site}`;
		},
		canUpdateInPlace() {
			if (!this.benchDocResource?.doc?.enable_inplace_updates) {
				return false;
			}

			// In Place updates cannot take place with removed apps.
			if (this.hasRemovedApps) {
				return false;
			}

			// All sites to be updated must belong to the same bench.
			const benches = new Set(this.selectedSites.map((s) => s.bench));
			if (benches.size !== 1) {
				return false;
			}

			// Failed in place update benches have to be regular updated.
			const inPlaceUpdateFailedBenches =
				this.benchDocResource?.doc?.inplace_update_failed_benches ?? [];

			const allSites = this.siteOptions.data
				.filter(
					(s) =>
						benches.has(s.bench) ||
						inPlaceUpdateFailedBenches.includes(s.bench),
				)
				.map((s) => s.name);

			// All sites under a bench should be updated
			if (allSites.length !== this.selectedSites.length) {
				return false;
			}

			return true;
		},
	},
	resources: {
		deployAndUpdate() {
			return {
				url: 'press.api.bench.deploy_and_update',
				params: {
					name: this.bench,
					apps: this.selectedApps,
					sites: this.selectedSites,
					run_will_fail_check: !this.ignoreWillFailCheck,
				},
				validate() {
					if (
						this.hasUpdateAvailable &&
						this.selectedApps.length === 0 &&
						this.deployInformation.removed_apps.length === 0
					) {
						throw new DashboardError('Please select an app to proceed');
					}
				},
				onSuccess(candidate) {
					this.$router.push({
						name: 'Deploy Candidate',
						params: {
							id: candidate,
							name: this.bench,
						},
					});
					this.restrictMessage = '';
					this.show = false;
					this.$emit('success', candidate);
				},
				onError: this.setErrorMessage.bind(this),
			};
		},
		updateInPlace() {
			return {
				url: 'press.api.bench.update_inplace',
				params: {
					name: this.bench,
					apps: this.selectedApps,
					sites: this.selectedSites,
				},
				onSuccess(id) {
					this.$router.push({
						name: 'Release Group Job',
						params: { id },
					});

					this.restrictMessage = '';
					this.show = false;
					this.$emit('success', null);
				},
				onError: this.setErrorMessage.bind(this),
			};
		},
	},
	methods: {
		updateNextRelease(name, nextRelease, nextReleaseHash = null) {
			const app = this.benchDocResource.doc.deploy_information.apps.find(
				(a) => a.name === name,
			);
			if (app) {
				app.next_release = nextRelease;
				app.next_release_hash = nextReleaseHash;
			}

			// Update next_release in selectedApps as well
			this.handleAppSelection(this.selectedApps.map((a) => a.app));
		},
		back() {
			if (this.step === 'select-apps') {
				return;
			} else if (this.step === 'removed-apps') {
				this.step = 'select-apps';
			} else if (this.step === 'select-sites' && this.hasRemovedApps) {
				this.step = 'removed-apps';
			} else if (this.step === 'select-sites' && !this.hasRemovedApps) {
				this.step = 'select-apps';
			} else if (this.step === 'restrict-build') {
				this.step = 'select-sites';
			}

			if (this.step === 'select-apps') {
				this.selectedApps = [];
			}
		},
		next() {
			if (this.errorMessage) {
				this.errorMessage = '';
			}

			if (this.step === 'select-apps' && this.selectedApps.length === 0) {
				this.errorMessage = 'Please select an app to proceed';
				return;
			} else if (this.step === 'select-apps' && this.hasRemovedApps) {
				this.step = 'removed-apps';
			} else if (this.step === 'select-apps' && !this.hasRemovedApps) {
				this.step = 'select-sites';
			} else if (this.step === 'removed-apps') {
				this.step = 'select-sites';
			} else if (this.step === 'select-sites' && this.restrictMessage) {
				this.step = 'restrict-build';
			}
		},
		handleAppSelection(apps) {
			apps = Array.from(apps);
			let appData = this.benchDocResource.doc.deploy_information.apps;

			this.selectedApps = appData
				.filter((app) => apps.includes(app.name))
				.map((app) => {
					return {
						app: app.name,
						source: app.source,
						release: app.releases.find(
							(release) =>
								release.name === app.next_release && !release.is_yanked,
						)?.name,
						hash: app.releases.find(
							(release) =>
								release.name === app.next_release && !release.is_yanked,
						)?.hash,
					};
				});
		},
		handleSiteSelection(sites) {
			sites = Array.from(sites);
			let siteData = this.benchDocResource.doc.deploy_information.sites;

			this.selectedSites = siteData.filter((site) => sites.includes(site.name));
		},
		deployFrom(app) {
			if (app.will_branch_change) {
				return app.current_branch;
			}
			return app.current_hash
				? app.current_tag || app.current_hash.slice(0, 7)
				: null;
		},
		initialDeployTo(app) {
			return this.benchDocResource.doc.deploy_information.apps.find(
				(a) => a.app === app.app,
			).next_release;
		},
		updateBench() {
			if (this.selectedApps.length === 0 && !this.lastDeploy) {
				this.errorMessage = 'Please select an app to proceed';
				return;
			}

			if (this.restrictMessage && !this.ignoreWillFailCheck) {
				this.errorMessage =
					'Please check the <b>I understand</b> box to proceed';
				return;
			}

			this.errorMessage = '';
			if (this.canUpdateInPlace && this.useInPlaceUpdate) {
				this.setSkipBackupsAndFailingPatches();
				this.$resources.updateInPlace.submit();
			} else {
				this.$resources.deployAndUpdate.submit();
			}
		},
		setSkipBackupsAndFailingPatches() {
			for (const site of this.selectedSites) {
				site.skip_failing_patches = true;
				site.skip_backups = true;
			}
		},
		setErrorMessage(error) {
			this.ignoreWillFailCheck = false;
			if (error?.exc_type === 'BuildValidationError') {
				this.restrictMessage = error?.messages?.[0] ?? '';
			}

			if (error?.exc_type === 'InsufficientSpaceOnServer') {
				this.errorMessage = error?.messages?.[0] ?? '';
				return;
			}

			if (error?.exc_type === 'PermissionError') {
				this.errorMessage = error?.messages?.[0] ?? '';
				return;
			}

			if (this.restrictMessage) {
				this.step = 'restrict-build';
				return;
			}
			if (Array.isArray(error.messages)) {
				this.errorMessage = error.messages.join(', ');
			} else {
				this.errorMessage =
					'Internal Server Error: Deploy could not be initiated';
			}
		},
	},
};
</script>
