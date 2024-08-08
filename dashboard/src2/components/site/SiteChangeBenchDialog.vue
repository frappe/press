<template>
	<Dialog
		:options="{
			title: 'Move Site to another Bench',
			actions: [
				{
					label: 'Change Bench',
					loading: $resources.changeGroup.loading,
					disabled: !$resources.changeGroupOptions?.data?.length,
					variant: 'solid',
					onClick: () =>
						$resources.changeGroup.submit({
							skip_failing_patches: skipFailingPatches,
							group: targetGroup,
							name: site
						})
				},
				{
					label: 'Clone current Bench',
					onClick: () => {
						$emit('update:modelValue', false);
						showCloneBenchDialog = true;
					}
				}
			]
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
					label="Select Bench"
					type="select"
					:options="
						$resources.changeGroupOptions.data.map(group => ({
							label: group.title,
							value: group.name
						}))
					"
					v-model="targetGroup"
				/>
				<FormControl
					label="Skip failing patches if any"
					type="checkbox"
					v-model="skipFailingPatches"
				/>
			</div>
			<p v-else-if="!errorMessage" class="text-md text-base text-gray-800">
				There are no other benches that you own for this site to move to. You
				can clone this bench to move the site.
			</p>
			<ErrorMessage class="mt-3" :message="errorMessage" />
		</template>
	</Dialog>
	<Dialog
		:options="{
			title: 'Clone Bench',
			actions: [
				{
					label: 'Clone Bench',
					variant: 'solid',
					loading: $resources.cloneGroup.loading,
					onClick: () =>
						$resources.cloneGroup.submit({
							name: site,
							new_group_title: newGroupTitle,
							server: selectedServer
						})
				}
			]
		}"
		v-model="showCloneBenchDialog"
	>
		<template #body-content>
			<FormControl label="New Bench Name" v-model="newGroupTitle" />
			<FormControl
				v-if="$resources.serverOptions.data.length > 0"
				class="mt-4"
				label="Select Server"
				type="select"
				:options="$resources.serverOptions.data"
				v-model="selectedServer"
			/>
			<ErrorMessage :message="$resources.cloneGroup.error" />
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
			targetGroup: null,
			newGroupTitle: '',
			skipFailingPatches: false,
			showCloneBenchDialog: false,
			selectedServer: null
		};
	},
	computed: {
		errorMessage() {
			return (
				this.$resources.changeGroupOptions.error ||
				this.$resources.changeGroup.error ||
				this.$resources.cloneGroup.error
			);
		}
	},
	resources: {
		changeGroup() {
			return {
				url: 'press.api.site.change_group',
				onSuccess() {
					const destinationGroupTitle =
						this.$resources.changeGroupOptions.data.find(
							group => group.name === this.targetGroup
						).title;

					toast.success(
						`The site has been scheduled to move to the ${destinationGroupTitle} bench successfully.`
					);

					this.$router.push({
						name: 'Site Detail Jobs',
						params: {
							name: this.site
						}
					});

					this.targetGroup = null;
					this.show = false;
				}
			};
		},
		changeGroupOptions() {
			return {
				url: 'press.api.site.change_group_options',
				params: {
					name: this.site
				},
				initialData: [],
				onSuccess(data) {
					if (data.length > 0) this.targetGroup = data[0].name;
				},
				auto: true
			};
		},
		cloneGroup() {
			return {
				url: 'press.api.site.clone_group',
				onSuccess(data) {
					toast.success(
						'The current bench has been cloned successfully. Redirecting to the new bench...'
					);
					this.showCloneBenchDialog = false;

					this.$router.push({
						name: 'Bench Deploy',
						params: {
							name: data.bench_name,
							id: data.candidate_name
						}
					});
				}
			};
		},
		serverOptions() {
			return {
				type: 'list',
				doctype: 'Server',
				fields: ['name', 'title'],
				auto: true,
				transform(data) {
					return data.map(server => ({
						label: server.title,
						value: server.name
					}));
				}
			};
		}
	}
};
</script>
