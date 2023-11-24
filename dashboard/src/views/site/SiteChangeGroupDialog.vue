<template>
	<Dialog
		:options="{
			title: 'Move Site to another Bench',
			actions: [
				{
					label: 'Clone current Bench',
					loading: $resources.cloneGroup.loading,
					onClick: () =>
						$resources.cloneGroup.submit({
							name: site?.name,
							group: targetGroup
						})
				},
				{
					label: 'Change Bench',
					loading: this.$resources.changeGroup.loading,
					disabled: !$resources.changeGroupOptions?.data?.length,
					variant: 'solid',
					onClick: () =>
						$resources.changeGroup.submit({
							group: targetGroup,
							name: site?.name
						})
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
			<FormControl
				v-else-if="$resources.changeGroupOptions.data.length > 0"
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
			<p v-else class="text-md text-base text-gray-800">
				There are no other benches that you own for this site to move to. You
				can clone this bench to move the site.
			</p>
			<ErrorMessage
				class="mt-3"
				:message="$resources.changeGroup.error || $resources.cloneGroup.error"
			/>
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	name: 'SiteChangeGroupDialog',
	props: ['site', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			targetGroup: null
		};
	},
	watch: {
		show(value) {
			if (value) this.$resources.changeGroupOptions.fetch();
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
		changeGroup() {
			return {
				url: 'press.api.site.change_group',
				params: {
					name: this.site?.name
				},
				onSuccess() {
					const destinationGroupTitle =
						this.$resources.changeGroupOptions.data.find(
							group => group.name === this.targetGroup
						).title;

					notify({
						title: 'Scheduled Bench Change',
						message: `Site scheduled to be moved to <b>${destinationGroupTitle}</b>`,
						color: 'green',
						icon: 'check'
					});
					this.targetGroup = null;
					this.$emit('update:modelValue', false);
				}
			};
		},
		changeGroupOptions() {
			return {
				url: 'press.api.site.change_group_options',
				params: {
					name: this.site?.name
				},
				initialData: [],
				onSuccess(data) {
					if (data.length > 0) this.targetGroup = data[0].name;
				}
			};
		},
		cloneGroup() {
			return {
				url: 'press.api.site.clone_group',
				onSuccess(data) {
					notify({
						title: 'Cloned Bench',
						message: `The current bench has been cloned successfully. Redirecting to the new bench...`,
						color: 'green',
						icon: 'check'
					});
					this.$emit('update:modelValue', false);
					this.$router.push({
						name: 'BenchDeploys',
						params: {
							benchName: data.bench_name,
							candidateName: data.candidate_name
						}
					});
				}
			};
		}
	}
};
</script>
