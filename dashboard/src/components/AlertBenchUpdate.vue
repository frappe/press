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
			Your bench is not deployed yet. Would you like to deploy now?
		</span>
		<template #actions>
			<Button
				type="primary"
				@click="$resources.deploy.submit()"
				:disabled="$resources.deploy.loading"
			>
				Deploy
			</Button>
		</template>
	</Alert>
</template>
<script>
export default {
	name: 'AlertBenchUpdate',
	props: ['bench'],
	resources: {
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
			return (
				['Awaiting Deploy', 'Active'].includes(this.bench.status) &&
				this.bench.update_available
			);
		}
	}
};
</script>
