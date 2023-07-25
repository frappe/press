<template>
	<Alert :title="alertTitle" v-if="show">
		<span v-if="deployInformation.deploy_in_progress"
			>A deploy for this bench is in progress</span
		>
		<span v-else-if="bench.status == 'Active'">
			A new update is available for your bench. Would you like to deploy the
			update now?
		</span>
		<span v-else>
			Your bench is not deployed yet. You can add more apps to your bench before
			deploying. If you want to deploy now, click on the Show Updates button.
		</span>
		<template #actions>
			<Button
				v-if="deployInformation.deploy_in_progress"
				appearance="primary"
				:route="`/benches/${bench.name}/deploys/${deployInformation.last_deploy.name}`"
				>View Progress</Button
			>
			<Button
				v-else
				appearance="primary"
				@click="
					() => {
						showDeployDialog = true;
						step = 'Apps';
					}
				"
			>
				Show Updates
			</Button>
		</template>

		<Dialog
			:options="{
				title:
					step == 'Apps'
						? 'Select the apps you want to update'
						: 'Select the sites you want to update'
			}"
			v-model="showDeployDialog"
		>
			<template v-slot:body-content>
				<BenchAppUpdates
					v-if="step == 'Apps'"
					:apps="deployInformation.apps"
					v-model:selectedApps="selectedApps"
					:removedApps="deployInformation.removed_apps"
				/>
				<BenchSiteUpdates
					v-if="step == 'Sites'"
					:sites="deployInformation.sites"
					v-model:selectedSites="selectedSites"
				/>
				<ErrorMessage class="mt-2" :message="errorMessage" />
			</template>
			<template v-slot:actions>
				<Button
					v-if="step == 'Sites'"
					appearance="primary"
					@click="$resources.deploy.submit()"
					:loading="$resources.deploy.loading"
				>
					{{ selectedSites.length > 0 ? 'Update' : 'Skip and Deploy' }}
				</Button>
				<Button v-if="step == 'Sites'" @click="step = 'Apps'"> Back </Button>
				<Button v-else appearance="primary" @click="step = 'Sites'">
					Next
				</Button>
			</template>
		</Dialog>
	</Alert>
</template>
<script>
import BenchAppUpdates from './BenchAppUpdates.vue';
import BenchSiteUpdates from './BenchSiteUpdates.vue';
import SwitchTeamDialog from './SwitchTeamDialog.vue';
export default {
	name: 'AlertBenchUpdate',
	props: ['bench'],
	components: {
		BenchAppUpdates,
		BenchSiteUpdates,
		SwitchTeamDialog
	},
	data() {
		return {
			showDeployDialog: false,
			showTeamSwitcher: false,
			selectedApps: [],
			selectedSites: [],
			step: 'Apps'
		};
	},
	resources: {
		deployInformation() {
			return {
				method: 'press.api.bench.deploy_information',
				params: {
					name: this.bench?.name
				},
				auto: true
			};
		},
		deploy() {
			let appsToIgnore = [];
			if (this.deployInformation) {
				appsToIgnore = Array.from(
					this.deployInformation.apps.filter(
						app => app.update_available && !this.selectedApps.includes(app.app)
					)
				);
			}

			return {
				method: 'press.api.bench.deploy_and_update',
				params: {
					name: this.bench?.name,
					apps_to_ignore: appsToIgnore,
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
				onSuccess() {
					this.showDeployDialog = false;
					this.$notify({
						title: 'Updates scheduled successfully',
						icon: 'check',
						color: 'green'
					});
				}
			};
		}
	},
	computed: {
		show() {
			if (this.deployInformation) {
				return (
					this.deployInformation.update_available &&
					['Awaiting Deploy', 'Active'].includes(this.bench.status)
				);
			}
		},
		errorMessage() {
			return (
				this.$resources.deploy.error ||
				(this.bench.team !== $account.team.name
					? "Current Team doesn't have enough permissions"
					: '')
			);
		},
		deployInformation() {
			return this.$resources.deployInformation.data;
		},
		alertTitle() {
			if (this.deployInformation && this.deployInformation.deploy_in_progress) {
				return 'Deploy in Progress';
			}
			return this.bench.status == 'Active' ? 'Update Available' : 'Deploy';
		}
	}
};
</script>
