<template>
	<Card
		title="Dependencies"
		subtitle="Update dependencies for your bench"
		:loading="$resources.dependencies.loading"
	>
		<template #actions>
			<Button
				v-if="isDirty"
				label="Update"
				@click="$resources.updateDependencies.submit()"
				:loading="$resources.updateDependencies.loading"
			/>
		</template>
		<FormControl
			v-for="dependency in $resources.dependencies.data"
			:key="dependency.key"
			v-model="dependency.value"
			:label="dependency.key.split('_').join(' ')"
			class="mx-0.5 my-2"
			@input="isDirty = true"
		/>
	</Card>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	name: 'BenchDependencies',
	props: ['benchName'],
	data() {
		return {
			isDirty: false
		};
	},
	resources: {
		dependencies() {
			return {
				url: 'press.api.bench.dependencies',
				params: {
					name: this.benchName
				},
				auto: true,
				initialData: []
			};
		},
		updateDependencies() {
			return {
				url: 'press.api.bench.update_dependencies',
				params: {
					name: this.benchName,
					dependencies: JSON.stringify(this.$resources.dependencies.data)
				},
				validate() {
					if (!this.isDirty) return 'No changes made';
				},
				onSuccess() {
					this.isDirty = false;
				},
				onError(err) {
					notify({
						title: 'Error',
						message: (err.messages || err.message.split('_')).join(', '),
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	}
};
</script>
