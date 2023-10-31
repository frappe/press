<template>
	<Dialog
		:options="{
			title: 'Move Site to another Bench',
			actions: [
				{
					label: 'Submit',
					loading: this.$resources.changeGroup.loading,
					variant: 'solid',
					onClick: () =>
						$resources.changeGroup.submit({
							group: targetGroup.name,
							name: siteName
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
			<ChangeGroupSelector
				v-else
				:groups="$resources.changeGroupOptions.data.groups"
				:selectedGroup="targetGroup"
				@update:selectedGroup="value => (targetGroup = value)"
			/>
			<ErrorMessage class="mt-3" :message="$resources.changeGroup.error" />
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';
import ChangeGroupSelector from '@/components/ChangeGroupSelector.vue';

export default {
	name: 'SiteChangeGroupDialog',
	props: ['siteName', 'modelValue'],
	emits: ['update:modelValue'],
	components: {
		ChangeGroupSelector
	},
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
					name: this.siteName
				},
				onSuccess() {
					notify({
						title: 'Scheduled Bench Change',
						message: `Site scheduled to be moved to ${this.targetGroup.title}`,
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
					name: this.siteName
				}
			};
		}
	}
};
</script>
