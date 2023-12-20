<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{
			title: 'Move Site to another Server',
			actions: [
				{
					label: 'Add Server to Bench',
					loading: $resources.addServerToReleaseGroup.loading,
					disabled: $resources.isServerAddedInGroup.data || !targetServer,
					onClick: () => $resources.addServerToReleaseGroup.submit()
				},
				{
					label: 'Change Server',
					loading: $resources.changeServer.loading,
					variant: 'solid',
					disabled:
						!$resources.changeServerOptions?.data?.length ||
						!targetServer ||
						!$resources.isServerAddedInGroup.data,
					onClick: () => {
						$resources.changeServer.submit({
							name: site?.name,
							server: targetServer,
							scheduled_datetime: datetimeInIST
						});
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
				@change="
					e =>
						$resources.isServerAddedInGroup.fetch({
							name: site?.name,
							server: e.target.value
						})
				"
			/>
			<FormControl
				class="mt-4"
				v-if="$resources.isServerAddedInGroup.data"
				label="Schedule Site Migration"
				type="datetime-local"
				:min="new Date().toISOString().slice(0, 16)"
				v-model="targetDateTime"
			/>
			<p class="mt-4 text-sm text-gray-700">
				{{ message }}
			</p>
			<ErrorMessage
				class="mt-4"
				:message="
					$resources.changeServer.error ||
					$resources.isServerAddedInGroup.error ||
					$resources.addServerToReleaseGroup.error
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
			targetServer: '',
			targetDateTime: null
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
		},
		message() {
			if (this.targetServer && !this.$resources.isServerAddedInGroup.data) {
				return "The chosen server isn't added to the bench yet. Please add the server to the bench first.";
			} else if (
				this.targetServer &&
				this.$resources.isServerAddedInGroup.data
			) {
				return 'The chosen server is already added to the bench. You can now migrate the site to the server.';
			} else return '';
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime)
				.tz('Asia/Kolkata')
				.format('YYYY-MM-DDTHH:mm');

			return datetimeInIST;
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
				}
			};
		},
		isServerAddedInGroup() {
			return {
				url: 'press.api.site.is_server_added_in_group',
				initialData: false
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
		},
		addServerToReleaseGroup() {
			return {
				url: 'press.api.site.add_server_to_release_group',
				params: {
					name: this.site?.name,
					group_name: this.site?.group,
					server: this.targetServer
				},
				onSuccess(data) {
					notify({
						title: 'Server Added to the Bench',
						message: `Added <b>${this.targetServer}</b> to current bench. Please wait for the deploy to be completed.`,
						icon: 'check',
						color: 'green'
					});
					this.$router.push({
						name: 'BenchJobs',
						params: {
							benchName: this.site?.group,
							jobName: data
						}
					});
					this.resetValues();
					this.$emit('update:modelValue', false);
				}
			};
		}
	},
	methods: {
		resetValues() {
			this.targetServer = '';
			this.targetDateTime = null;
			this.$resources.isServerAddedInGroup.reset();
		}
	}
};
</script>
