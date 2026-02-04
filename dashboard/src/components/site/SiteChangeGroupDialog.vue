<template>
	<Dialog
		:options="{
			title: 'Move Site to another Bench Group',
			actions: [
				{
					label: 'Change Bench Group',
					loading: $resources.changeGroup.loading,
					variant: 'solid',
					onClick: () =>
						$resources.changeGroup.submit({
							skip_failing_patches: skipFailingPatches,
							group: targetGroup.value,
							name: site,
						}),
				}
			],
		}"
		v-model="show"
	>
		<template #body-content>
			<LoadingIndicator
				class="mx-auto h-4 w-4"
				v-if="$resources.changeGroupOptions.loading"
			/>
			<div
				v-else-if="$resources.changeGroupOptions.data.length > 0"
				class="space-y-4"
			>
				<FormControl
					variant="outline"
					label="Select Bench Group"
					type="combobox"
					:options="
						$resources.changeGroupOptions.data.map((group) => ({
							label: group.title || group.name,
							description: group.name,
							value: group.name,
						}))
					"
					:modelValue="targetGroup?.value"
					@update:modelValue="
						targetGroup = $resources.changeGroupOptions.data
							.map((group) => ({
								label: group.title || group.name,
								description: group.name,
								value: group.name,
							}))
							.find((option) => option.value === $event)
					"
				/>
				<FormControl
					label="Skip failing patches if any"
					type="checkbox"
					v-model="skipFailingPatches"
				/>
			</div>
			<p v-else-if="!errorMessage" class="text-md text-base text-gray-800">
				There are no other bench groups that you own for this site to move to.
				You have to create a new bench group first.

				<FormControl label="New Bench Group Name" v-model="newGroupTitle" class="mt-4" />
				<FormControl
				v-if="$resources.serverOptions.data && $resources.serverOptions.data.length > 0"
					class="mt-4"
					label="Select Server"
					type="select"
					:options="$resources.serverOptions.data"
					v-model="selectedServer"
				/>
				</p>
				<ErrorMessage class="mt-3" :message="errorMessage" />
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';

export default {
	props: ['site'],
	data() {
		return {
			show: true,
			targetGroup: {
				label: '',
				value: '',
			},
			newGroupTitle: '',
			skipFailingPatches: false,
			showCloneBenchDialog: false,
			selectedServer: null,
		};
	},
	computed: {
		errorMessage() {
			return (
				this.$resources.changeGroupOptions.error ||
				this.$resources.changeGroup.error
			);
		},
	},
	resources: {
		changeGroup() {
			return {
				url: 'press.api.site.change_group',
				onSuccess() {
					const destinationGroupTitle =
						this.$resources.changeGroupOptions.data.find(
							(group) => group.name === this.targetGroup.value,
						).title;

					toast.success(
						`The site has been scheduled to move to the ${destinationGroupTitle} bench group successfully.`,
					);

					this.$router.push({
						name: 'Site Jobs',
						params: {
							name: this.site,
						},
					});

					this.targetGroup = {
						label: '',
						value: '',
					};
					this.show = false;
				},
			};
		},
		changeGroupOptions() {
			return {
				url: 'press.api.site.change_group_options',
				params: {
					name: this.site,
				},
				initialData: [],
				onSuccess(data) {
					if (data.length > 0) this.targetGroup.value = data[0].name;
				},
				auto: true,
			};
		},
		serverOptions() {
			return {
				type: 'list',
				doctype: 'Server',
				fields: ['name', 'title'],
				auto: true,
				initialData: [],
				transform(data) {
					return data.map((server) => ({
						label: server.title,
						value: server.name,
					}));
				},
			};
		},
	},
};
</script>
