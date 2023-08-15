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
				variant="solid"
				:route="`/benches/${bench.name}/deploys/${deployInformation.last_deploy.name}`"
				>View Progress</Button
			>
			<Tooltip
				v-else
				:text="
					!permissions.update
						? `You don't have enough permissions to perform this action`
						: 'Show Updates'
				"
			>
				<Button
					variant="solid"
					:disabled="!permissions.update"
					@click="showDeployDialog = true"
				>
					Show updates
				</Button>
			</Tooltip>
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
				<ErrorMessage class="mt-2" :message="errorMessage" />
			</template>
			<template v-slot:actions>
				<Button
					class="w-full"
					variant="solid"
					@click="$resources.deploy.submit()"
					:loading="$resources.deploy.loading"
					v-if="this.bench.team === $account.team.name"
				>
					Deploy
				</Button>
				<Button
					class="w-full"
					variant="solid"
					@click="showTeamSwitcher = true"
					v-else
				>
					Switch Team
				</Button>
				<SwitchTeamDialog v-model="showTeamSwitcher" />
			</template>
		</Dialog>
	</Alert>
</template>
<script>
import BenchAppUpdates from './BenchAppUpdates.vue';
import SwitchTeamDialog from './SwitchTeamDialog.vue';
export default {
	name: 'AlertBenchUpdate',
	props: ['bench'],
	components: {
		BenchAppUpdates,
		SwitchTeamDialog
	},
	data() {
		return {
			showDeployDialog: false,
			showTeamSwitcher: false,
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
					this.showDeployDialog = false;
				}
			};
		}
	},
	computed: {
		permissions() {
			return {
				update: this.$account.hasPermission(
					this.bench.name,
					'press.api.bench.deploy_and_update'
				)
			};
		},
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
