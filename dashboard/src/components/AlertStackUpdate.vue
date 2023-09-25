<template>
	<Alert :title="alertTitle" v-if="show">
		<span v-if="deployInformation.deploy_in_progress"
			>A deploy for this stack is in progress</span
		>
		<span v-else-if="stack.status == 'Active'">
			A new update is available for your stack. Would you like to deploy the
			update now?
		</span>
		<span v-else> Your stack is not deployed yet. </span>
		<template #actions>
			<Button
				v-if="deployInformation.deploy_in_progress"
				variant="solid"
				:route="`/stack/${stack.name}/deploys/${deployInformation.last_deploy.name}`"
				>View Progress</Button
			>
			<Button
				v-else
				variant="solid"
				class="w-full"
				@click="$resources.deploy.submit()"
				:loading="$resources.deploy.loading"
			>
				Deploy
			</Button>
		</template>
	</Alert>
</template>
<script>
export default {
	name: 'AlertStackUpdate',
	props: ['stack'],
	resources: {
		deployInformation() {
			return {
				url: 'press.api.stack.deploy_information',
				params: {
					name: this.stack?.name
				},
				auto: true
			};
		},
		deploy() {
			return {
				url: 'press.api.stack.deploy',
				params: {
					name: this.stack?.name
				},
				onSuccess(new_candidate_name) {
					this.$resources.deployInformation.setData({
						...this.$resources.deployInformation.data,
						deploy_in_progress: true,
						last_deploy: { name: new_candidate_name, status: 'Running' }
					});
					this.$resources.deployInformation.reload();
				}
			};
		}
	},
	computed: {
		show() {
			if (this.deployInformation) {
				return (
					this.deployInformation.update_available &&
					['Awaiting Deploy', 'Active'].includes(this.stack.status)
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
			return this.stack.status == 'Active' ? 'Update Available' : 'Deploy';
		}
	}
};
</script>
