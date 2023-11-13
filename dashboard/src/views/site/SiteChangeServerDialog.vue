<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{
			title: 'Move Site to another Server',
			actions: [
				{
					label: checkForBench ? 'Check for Available Benches' : 'Submit',
					loading: $resources.changeServer.loading,
					variant: 'solid',
					disabled: !$resources.changeServerOptions?.data?.length,
					onClick: () => {
						if (checkForBench) {
							$resources.changeServerBenchOptions.fetch();
						} else {
							$resources.changeServer.submit({
								name: site?.name,
								group: targetBench,
								scheduled_datetime: targetDateTime
							});
						}
					}
				}
			]
		}"
	>
		<template #body-content>
			<LoadingIndicator
				class="mx-auto h-4 w-4"
				v-if="$resources.changeServerOptions.loading"
			/>
			<FormControl
				v-else-if="$resources.changeServerOptions.data.length > 0"
				label="Select Server"
				type="select"
				:options="$resources.changeServerOptions.data"
				v-model="targetServer"
			/>
			<p v-else class="text-base">
				There are no servers available to move this site. Please create a new
				server first.
			</p>
			<FormControl
				class="mt-4"
				v-if="$resources.changeServerBenchOptions.data.length > 0"
				label="Select Bench"
				type="select"
				:options="$resources.changeServerBenchOptions.data"
				v-model="targetBench"
			/>
			<FormControl
				class="mt-4"
				v-if="$resources.changeServerBenchOptions.data.length > 0"
				label="Schedule Site Migration (IST)"
				type="datetime-local"
				:min="new Date().toISOString().slice(0, 16)"
				v-model="targetDateTime"
			/>
			<ErrorMessage
				class="mt-4"
				:message="
					$resources.changeServer.error ||
					$resources.changeServerBenchOptions.error
				"
			/>
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	name: 'SiteChangeServerDialog',
	props: ['site', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			targetBench: '',
			targetServer: '',
			targetDateTime: null,
			checkForBench: true
		};
	},
	watch: {
		show(value) {
			if (value) this.$resources.changeServerOptions.fetch();
		}
	},
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	},
	resources: {
		changeServerOptions() {
			return {
				url: 'press.api.site.change_server_options',
				params: {
					name: this.site?.name
				},
				transform(d) {
					return d.map(s => ({
						label: s.title || s.name,
						value: s.name
					}));
				},
				onSuccess(data) {
					if (data.length > 0) this.targetServer = data[0].name;
				}
			};
		},
		changeServerBenchOptions() {
			return {
				url: 'press.api.site.change_server_bench_options',
				params: {
					name: this.site?.name,
					server: this.targetServer
				},
				initialData: [],
				transform(d) {
					return d.map(s => ({
						label: s.title || s.name,
						value: s.name
					}));
				},
				onSuccess(data) {
					this.targetBench = data[0].name;
					this.checkForBench = false;
				}
			};
		},
		changeServer() {
			return {
				url: 'press.api.site.change_server',
				onSuccess() {
					notify({
						title: 'Site Change Server',
						message: `Site <b>${this.site?.name}</b> has been scheduled to move to <b>${this.targetServer}</b>`,
						icon: 'check',
						color: 'green'
					});
					this.$emit('update:modelValue', false);
				}
			};
		}
	},
	methods: {
		resetValues() {
			this.targetBench = '';
			this.targetServer = '';
			this.targetDateTime = null;
			this.checkForBench = true;
		}
	}
};
</script>
