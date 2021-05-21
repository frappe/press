<template>
	<Alert
		:title="bench.status == 'Active' ? 'Update Available' : 'Deploy'"
		v-if="show"
	>
		<span v-if="bench.status == 'Active'">
			A new update is available for your bench. Would you like to deploy the
			update now?
		</span>
		<span v-else>
			Your bench is not deployed yet. You can add more apps to your bench before
			deploying. If you want to deploy now, click on Deploy.
		</span>
		<template #actions>
			<Button type="primary" @click="showDeployDialog = true">
				Show updates
			</Button>
		</template>
		<Dialog title="Following updates are available" v-model="showDeployDialog">
			<AppUpdates :apps="deployInformation.apps" />
			<template #actions>
				<Button
					type="primary"
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
import AppUpdates from './AppUpdates.vue';
export default {
	name: 'AlertBenchUpdate',
	props: ['bench'],
	components: {
		AppUpdates
	},
	data() {
		return {
			showDeployDialog: false
		};
	},
	resources: {
		deployInformation() {
			return {
				method: 'press.api.bench.deploy_information',
				params: {
					name: this.bench.name
				},
				auto: true
			};
		},
		deploy() {
			return {
				method: 'press.api.bench.deploy',
				params: {
					name: this.bench.name
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
		}
	}
};
</script>
