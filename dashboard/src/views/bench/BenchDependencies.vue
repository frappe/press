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
				@click="
					$resources.updateDependencies.submit();
					isDirty = false;
				"
			/>
		</template>
		<table class="min-w-full divide-y divide-gray-300">
			<thead>
				<tr class="divide-x divide-gray-200">
					<th
						scope="col"
						class="py-3.5 pl-4 pr-4 text-left text-base font-semibold text-gray-900 sm:pl-0"
					>
						Dependency
					</th>
					<th
						scope="col"
						class="px-4 py-3.5 text-left text-base font-semibold text-gray-900"
					>
						Version
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-200 bg-white">
				<tr
					v-for="dependency in $resources.dependencies.data"
					:key="dependency.key"
					class="divide-x divide-gray-200"
				>
					<td
						class="whitespace-nowrap py-4 pl-4 pr-4 text-sm font-medium text-gray-900 sm:pl-0"
					>
						{{ dependency.key }}
					</td>
					<td class="whitespace-nowrap text-sm text-gray-500">
						<input
							class="border-none focus:text-gray-800 focus:ring-0"
							v-model="dependency.value"
							@input="isDirty = true"
						/>
					</td>
				</tr>
			</tbody>
		</table>
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
				onError(err) {
					notify({
						title: 'Error',
						message: err.messages.join(', '),
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	}
};
</script>
