<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{
			title: 'Move Site to another Server',
			actions: [
				{
					label: 'Add Server to Bench Group',
					loading: $resources.addServerToReleaseGroup.loading,
					disabled: $resources.isServerAddedInGroup.data || !targetServer.value,
					onClick: () => $resources.addServerToReleaseGroup.submit()
				},
				{
					label: 'Change Server',
					loading: $resources.changeServer.loading,
					variant: 'solid',
					disabled:
						!$resources.changeServerOptions?.data?.length ||
						!targetServer.value ||
						!$resources.isServerAddedInGroup.data,
					onClick: () => {
						$resources.changeServer.submit({
							name: site,
							server: targetServer.value,
							scheduled_datetime: datetimeInIST,
							skip_failing_patches: skipFailingPatches
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
				variant="outline"
				type="autocomplete"
				:options="$resources.changeServerOptions.data"
				v-model="targetServer"
			/>
			<div v-if="$resources.isServerAddedInGroup.data" class="mt-4 space-y-4">
				<DateTimeControl v-model="targetDateTime" label="Schedule Time" />
				<FormControl
					label="Skip failing patches if any"
					type="checkbox"
					v-model="skipFailingPatches"
				/>
			</div>
			<p v-if="message && !errorMessage" class="mt-4 text-sm text-gray-700">
				{{ message }}
			</p>
			<ErrorMessage class="mt-4" :message="errorMessage" />
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import DateTimeControl from '../DateTimeControl.vue';
import { toast } from 'vue-sonner';

export default {
	props: ['site'],
	components: { DateTimeControl },
	data() {
		return {
			show: true,
			targetServer: {
				label: '',
				value: ''
			},
			targetDateTime: null,
			skipFailingPatches: false
		};
	},
	watch: {
		targetServer(targetServer) {
			this.$resources.isServerAddedInGroup.fetch({
				name: this.site,
				server: targetServer.value
			});
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		message() {
			if (this.$resources.changeServerOptions.data.length === 0) {
				return 'No servers available for your team to move the site to. Please create a server first.';
			} else if (
				this.targetServer.value &&
				!this.$resources.isServerAddedInGroup.data
			) {
				return "The chosen server isn't added to the bench group yet. Please add the server to the bench groupfirst.";
			} else if (
				this.targetServer.value &&
				this.$resources.isServerAddedInGroup.data
			) {
				return 'The chosen server is already added to the bench. You can now migrate the site to the server.';
			} else return '';
		},
		errorMessage() {
			return (
				this.$resources.addServerToReleaseGroup.error ||
				this.$resources.isServerAddedInGroup.error ||
				this.$resources.changeServerOptions.error ||
				this.$resources.changeServer.error
			);
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime).format(
				'YYYY-MM-DDTHH:mm'
			);

			return datetimeInIST;
		}
	},
	resources: {
		changeServerOptions() {
			return {
				url: 'press.api.site.change_server_options',
				params: {
					name: this.site
				},
				initialData: [],
				auto: true,
				transform(d) {
					return d.map(s => ({
						label: s.title || s.name,
						description: s.name,
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
					toast.success('Site has been scheduled to move to another server.');
					this.show = false;
				}
			};
		},
		addServerToReleaseGroup() {
			return {
				url: 'press.api.site.add_server_to_release_group',
				params: {
					name: this.site,
					group_name: this.$site.doc?.group,
					server: this.targetServer.value
				},
				onSuccess(data) {
					toast.success(
						`Server ${this.targetServer.value} added to the bench. Please wait for the deploy to be completed.`
					);

					this.$router.push({
						name: 'Release Group Job',
						params: {
							name: this.$site.doc?.group,
							id: data
						}
					});

					this.show = false;
				}
			};
		}
	},
	methods: {
		resetValues() {
			this.targetServer = {
				label: '',
				value: ''
			};
			this.targetDateTime = null;
			this.$resources.isServerAddedInGroup.reset();
		}
	}
};
</script>
