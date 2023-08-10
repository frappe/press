<template>
	<Dialog
		:options="{
			title: 'Drop Bench',
			actions: [
				{
					label: 'Drop Bench',
					variant: 'solid',
					theme: 'red',
					loading: $resources.dropBench.loading,
					onClick: () => $resources.dropBench.submit()
				}
			]
		}"
		v-model="show"
	>
		<template v-slot:body-content>
			<p class="text-base">
				Are you sure you want to drop this bench? All the sites on this bench
				should be dropped manually before dropping the bench. This action cannot
				be undone.
			</p>
			<p class="mt-4 text-base">
				Please type
				<span class="font-semibold">{{ bench.title }}</span> to confirm.
			</p>
			<FormControl class="mt-4 w-full" v-model="confirmBenchName" />
			<ErrorMessage class="mt-2" :message="$resources.dropBench.error" />
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
			confirmBenchName: ''
		};
	},
	resources: {
		dropBench() {
			return {
				method: 'press.api.bench.archive',
				params: {
					name: this.bench?.name
				},
				onSuccess() {
					this.show = false;
					this.$router.push('/sites');
				},
				validate() {
					if (this.bench?.title !== this.confirmBenchName) {
						return 'Please type the bench name correctly to confirm';
					}
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
