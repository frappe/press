<template>
	<div>
		<div>
			<label class="text-lg font-semibold"> Choose a Bench </label>
			<p class="text-base text-gray-700">
				Choose a bench where you want to install the code server.
			</p>
		</div>
		<LoadingText v-if="$resources.options.loading" />
		<div v-else>
			<ListItem
				v-if="benches.length > 0"
				v-for="(bench, index) in benches"
				:key="bench"
				:title="bench"
				class="m-2 rounded-md border px-2 shadow-sm hover:cursor-pointer hover:shadow-md"
				:class="[
					modelValue && modelValue == bench
						? 'relative ring-2 ring-inset ring-blue-500'
						: ''
				]"
				v-on:click="selectBench(bench)"
			>
				<template #actions>
					<Badge v-if="index === 0" label="Latest Deployed"></Badge>
				</template>
			</ListItem>
			<div v-else class="ml-2 mt-4 text-sm">
				No bench versions found with a code server. Click
				<router-link
					:to="`/benches/${selectedGroup}`"
					class="text-blue-600 hover:underline"
					>here</router-link
				>
				to deploy a new available version of your bench.
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'NewCodeServerBench',
	props: ['modelValue', 'selectedGroup'],
	emits: ['update:modelValue', 'error'],
	methods: {
		selectBench(bench) {
			this.$emit('update:modelValue', bench);
		}
	},
	resources: {
		options() {
			return {
				url: 'press.api.spaces.code_server_bench_options',
				params: {
					group: this.selectedGroup
				},
				auto: true
			};
		}
	},
	computed: {
		benches() {
			if (!this.$resources.options.data) {
				return [];
			}
			return this.$resources.options.data;
		}
	}
};
</script>
