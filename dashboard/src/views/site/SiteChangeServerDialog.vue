<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Move Site to another Server',
			actions: [
				{
					label: 'Submit',
					loading: this.$resources.changeServer.loading,
					variant: 'solid',
					onClick: () =>
						$resources.changeServer.submit({
							server: targetServer,
							name: site?.name
						})
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
				There are no servers available to move this site.
			</p>
			<ErrorMessage class="mt-4" :message="$resources.changeServer.error" />
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
			targetServer: ''
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
						label: s.name,
						value: s.name
					}));
				},
				onSuccess() {
					this.targetServer = this.$resources.changeServerOptions.data[0].value;
				}
			};
		},
		changeServer() {
			return {
				url: 'press.api.site.change_server',
				params: {
					name: this.site?.name,
					server: this.targetServer
				},
				onSuccess() {
					notify({
						title: 'Site Change Server',
						message: `Site ${this.site?.name} has been scheduled to move to ${this.targetServer}`,
						icon: 'check',
						color: 'green'
					});
					this.$emit('update:modelValue', false);
				}
			};
		}
	}
};
</script>
