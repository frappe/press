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
			v-for="dependency in activeDependencies"
			:key="dependency.key"
			type="select"
			v-model="dependency.value"
			:options="dependencySelectOptions(dependency.key)"
			:value="dependency.value"
			:label="dependencies.dependency_title[dependency.key]"
			class="mx-0.5 my-2"
			@input="isDirty = true"
		/>
		<p
			v-if="dependencies.update_available"
			class="ml-0.5 mt-2.5 text-base text-red-600"
		>
			The changes will take effect in your next bench deploy.
		</p>
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
					dependencies: JSON.stringify(this.dependencies.active_dependencies)
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
	},
	computed: {
		dependencies() {
			return this.$resources.dependencies.data;
		},
		activeDependencies() {
			return this.dependencies.active_dependencies.filter(
				dependency =>
					!this.dependencies.internal_dependencies.includes(dependency.key)
			);
		}
	},
	methods: {
		dependencySelectOptions(dependency) {
			let versions_for_specific_package =
				this.dependencies.supported_dependencies.filter(
					dep => dep.key === dependency
				);
			return versions_for_specific_package.map(dep => ({
				label: dep.value,
				value: dep.value
			}));
		}
	}
};
</script>
