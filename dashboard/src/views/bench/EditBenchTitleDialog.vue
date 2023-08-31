<template>
	<Dialog
		:options="{
			title: 'Edit Title',
			actions: [
				{
					label: 'Update',
					variant: 'solid',
					loading: $resources.editTitle.loading,
					onClick: () => $resources.editTitle.submit()
				}
			]
		}"
		v-model="show"
	>
		<template v-slot:body-content>
			<FormControl label="Title" type="text" v-model="benchTitle" />
			<ErrorMessage class="mt-4" :message="$resources.editTitle.error" />
		</template>
	</Dialog>
</template>
<script>
export default {
	name: 'EditBenchTitleDialog',
	props: ['modelValue', 'bench'],
	emits: ['update:modelValue'],
	data() {
		return {
			benchTitle: this.bench.title
		};
	},
	resources: {
		editTitle() {
			return {
				url: 'press.api.bench.rename',
				params: {
					name: this.bench?.name,
					title: this.benchTitle
				},
				validate() {
					if (this.benchTitle === this.bench?.title) {
						return 'No changes in bench title';
					}
				},
				onSuccess() {
					this.show = false;
					this.bench.title = this.benchTitle;
				}
			};
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
	}
};
</script>
