<template>
	<Dialog
		:options="{
			title: 'Database Process',
			size: 'xl',
		}"
		v-model="show"
		:modelValue="true"
	>
		<template #body-content>
			<div class="flex flex-col gap-1">
				<p class="ml-1 font-mono text-sm">Host: {{ host }}</p>
				<p class="ml-1 font-mono text-sm">User: {{ user }}</p>
				<p class="ml-1 font-mono text-sm" v-if="state">State: {{ state }}</p>
				<p class="ml-1 font-mono text-sm" v-if="command">
					Command: {{ command }}
				</p>

				<div v-if="query">
					<p class="ml-1 font-mono text-sm">Query:</p>
					<pre
						class="mt-1 whitespace-pre-wrap rounded-lg border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700"
						>{{ query }}</pre
					>
				</div>
				<ErrorMessage
					class="mt-2"
					:message="$resources.killDatabaseProcess.error"
				/>
				<div class="mt-2 flex text-sm">
					<Button
						variant="solid"
						theme="red"
						class="w-full"
						@click="$resources.killDatabaseProcess.submit()"
						:loading="$resources.killDatabaseProcess.loading"
						loadingText="Killing Database Process"
					>
						Kill Database Process
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
export default {
	name: 'SiteDatabaseProcess',
	props: ['id', 'query', 'user', 'host', 'state', 'command', 'site'],
	emits: ['process-killed'],
	data() {
		return {
			show: true,
		};
	},
	resources: {
		killDatabaseProcess() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'kill_database_process',
						args: {
							id: this.id,
						},
					};
				},
				onSuccess: () => {
					this.$emit('process-killed');
				},
			};
		},
	},
};
</script>
