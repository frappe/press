<template>
	<Dialog
		v-model="show"
		:options="{
			size: '2xl',
			title: 'Update Bench'
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<div v-if="step === 'select-apps'">
					<div class="mb-4 text-lg font-medium">Select apps to update</div>
					<GenericList
						v-if="benchDocResource.doc.deploy_information.update_available"
						:options="updatableAppOptions"
						@update:selections="handleAppSelection"
					/>
					<div v-else class="text-center text-base text-gray-600">
						No apps to update
					</div>
				</div>
				<div v-else-if="step === 'removed-apps'">
					<div class="mb-4 text-lg font-medium">These apps will be removed</div>
					<GenericList :options="removedAppOptions" />
				</div>
				<div v-else-if="step === 'select-sites'">
					<div class="mb-4 text-lg font-medium">Select sites to update</div>
					<GenericList
						v-if="benchDocResource.doc.deploy_information.sites.length"
						:options="siteOptions"
						@update:selections="handleSiteSelection"
					/>
					<div
						class="text-center text-base font-medium text-gray-600"
						v-else-if="!benchDocResource.doc.deploy_information.sites.length"
					>
						No active sites to update
					</div>
				</div>
				<ErrorMessage :message="$resources.deploy.error" />
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-between space-y-2">
				<div v-if="step === 'select-apps'"></div>
				<Button
					v-if="
						step !== 'select-apps' &&
						!(
							step === 'removed-apps' &&
							!benchDocResource.doc.deploy_information.apps.some(
								app => app.update_available === true
							)
						)
					"
					label="Back"
					@click="
						benchDocResource.doc.deploy_information.removed_apps.length &&
						step === 'select-sites'
							? (step = 'removed-apps')
							: (step = 'select-apps');
						selectedApps = new Set();
					"
				/>
				<Button
					v-if="step === 'select-apps' || step === 'removed-apps'"
					variant="solid"
					label="Next"
					@click="next"
				/>
				<Button
					v-if="step === 'select-sites'"
					variant="solid"
					:label="
						selectedSites.length > 0
							? `Deploy and update ${selectedSites.length} ${$format.plural(
									selectedSites.length,
									'site',
									'sites'
							  )}`
							: 'Skip and Deploy'
					"
					:loading="$resources.deploy.loading"
					@click="$resources.deploy.submit()"
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

export default {
	name: 'UpdateBenchDialog',
	props: ['bench'],
	components: { GenericList, CommitChooser, CommitTag },
	data() {
		return {
			show: true,
			step: '',
			selectedApps: [],
			selectedSites: []
		};
	},
	mounted() {
		this.step = this.benchDocResource.doc.deploy_information.apps.some(
			app => app.update_available === true
		)
			? 'select-apps'
			: 'removed-apps';
	},
	computed: {
		updatableAppOptions() {
			let deployInformation = this.benchDocResource.doc.deploy_information;
			let appData = deployInformation.apps.filter(
				app => app.update_available === true
			);

			return {
				data: appData,
				selectable: true,
				columns: [
					{
						label: 'App',
						fieldname: 'title',
						width: 1.75
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
								link: `${app.repository_url}/commit/${tag}`
							});
						}
					},
					{
						label: 'To',
						fieldname: 'next_release',
						type: 'Component',
						component({ row: app }) {
							if (app.will_branch_change) {
								return h(CommitTag, {
									tag: app.branch,
									link: `${app.repository_url}/commit/${app.branch}`
								});
							}

							function commitChooserOptions(app) {
								return app.releases.map(release => {
									const messageMaxLength = 75;
									let message = release.message.split('\n')[0];
									message =
										message.length > messageMaxLength
											? message.slice(0, messageMaxLength) + '...'
											: message;

									return {
										label: release.tag
											? release.tag
											: `${message} (${release.hash.slice(0, 7)})`,
										value: release.name
									};
								});
							}

							function initialDeployTo(app) {
								let next_release = app.releases.filter(
									release => release.name === app.next_release
								)[0];
								if (app.will_branch_change) {
									return app.branch;
								} else {
									return next_release.tag || next_release.hash.slice(0, 7);
								}
							}

							if (!app.releases.length) return undefined;

							let initialValue = {
								label: initialDeployTo(app),
								value: app.next_release
							};

							return h(CommitChooser, {
								options: commitChooserOptions(app),
								modelValue: initialValue,
								'onUpdate:modelValue': value => {
									appData.find(app => app.name === app.name).next_release =
										value.value;
								}
							});
						}
					},
					{
						label: 'Status',
						fieldname: 'title',
						type: 'Badge',
						format(value, row) {
							if (
								deployInformation.removed_apps.find(
									app => app.name === row.name
								)
							) {
								return 'Will be Uninstalled';
							} else if (!row.will_branch_change && !row.current_hash) {
								return 'First Deploy';
							}
							return 'Update Available';
						}
					}
				]
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
						fieldname: 'title'
					},
					{
						label: 'Status',
						fieldname: 'name',
						type: 'Badge',
						format() {
							return 'Will be Uninstalled';
						}
					}
				]
			};
		},
		siteOptions() {
			let deployInformation = this.benchDocResource.doc.deploy_information;
			let siteData = deployInformation.sites;
			let team = getTeam();

			return {
				data: siteData,
				selectable: true,
				columns: [
					{
						label: 'Site',
						fieldname: 'name'
					},
					{
						label: 'Skip failed patches',
						fieldname: 'skip_failing_patches',
						width: 0.5,
						type: 'Component',
						component({ row }) {
							return h(Checkbox, {
								modelValue: row.skip_failing_patches
							});
						}
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
								modelValue: row.skip_backups
							});
						}
					}
				]
			};
		},
		benchDocResource() {
			return getCachedDocumentResource('Release Group', this.bench);
		},
		deployInformation() {
			return this.benchDocResource?.doc.deploy_information;
		}
	},
	resources: {
		deploy() {
			return {
				url: 'press.api.bench.deploy_and_update',
				params: {
					name: this.bench,
					apps: this.selectedApps,
					sites: this.selectedSites
				},
				validate() {
					if (
						this.selectedApps.length === 0 &&
						this.deployInformation.removed_apps.length === 0
					) {
						return 'You must select atleast 1 app to proceed with update.';
					}
				},
				onSuccess(candidate) {
					this.$router.push({
						name: 'Bench Deploy',
						params: {
							id: candidate
						}
					});
					this.show = false;
				}
			};
		}
	},
	methods: {
		next() {
			if (this.step === 'select-apps' && this.selectedApps.length === 0) {
				return;
			}
			if (
				this.benchDocResource.doc.deploy_information.removed_apps.length &&
				this.step === 'select-apps'
			) {
				this.step = 'removed-apps';
			} else {
				this.step = 'select-sites';
			}
		},
		handleAppSelection(apps) {
			apps = Array.from(apps);
			let appData = this.benchDocResource.doc.deploy_information.apps;

			this.selectedApps = appData
				.filter(app => apps.includes(app.name))
				.map(app => {
					return {
						app: app.name,
						source: app.source,
						release: app.next_release,
						hash: app.releases.find(
							release => release.name === app.next_release
						).hash
					};
				});
		},
		handleSiteSelection(sites) {
			sites = Array.from(sites);
			let siteData = this.benchDocResource.doc.deploy_information.sites;

			this.selectedSites = siteData.filter(site => sites.includes(site.name));
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
				a => a.app === app.app
			).next_release;
		}
	}
};
</script>
