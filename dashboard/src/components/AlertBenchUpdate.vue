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
			deploying. If you want to deploy now, click on Deploy.
		</span>
		<template #actions>
			<Button
				v-if="deployInformation.deploy_in_progress"
				appearance="primary"
				:route="`/benches/${bench.name}/deploys/${deployInformation.last_deploy.name}`"
				>View Progress</Button
			>
			<Button v-else appearance="primary" @click="showDeployDialog = true">
				Show updates
			</Button>
		</template>

		<Dialog
			:options="{ title: 'Select the apps you want to update' }"
			v-model="showDeployDialog"
		>
			<template v-slot:body-content>
				<BenchAppUpdates
					:apps="deployInformation.apps"
					v-model:selectedApps="selectedApps"
					:removedApps="deployInformation.removed_apps"
				/>
				<ErrorMessage class="mt-2" :message="$resources.deploy.error" />
			</template>
			<template v-slot:actions>
				<Button
					appearance="primary"
					@click="$resources.deploy.submit()"
					:loading="$resources.deploy.loading"
				>
					Deploy
				</Button>
			</template>
		</Dialog>
	</Alert>
</template>
<script>
import BenchAppUpdates from './BenchAppUpdates.vue';
export default {
	name: 'AlertBenchUpdate',
	props: ['bench'],
	components: {
		BenchAppUpdates
	},
	data() {
		return {
			showDeployDialog: false,
			selectedApps: []
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
				method: 'press.api.bench.deploy',
				params: {
					name: this.bench?.name,
					apps_to_ignore: appsToIgnore
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
					this.$router.push(`/benches/${this.bench.name}/deploys/${candidate}`);
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
