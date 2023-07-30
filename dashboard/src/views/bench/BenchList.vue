<template>
	<div
		class="sm:rounded-md sm:border sm:border-gray-100 sm:py-1 sm:px-2 sm:shadow"
	>
		<div
			class="py-2 text-base text-gray-600 sm:px-2"
			v-if="benches.length === 0"
		>
			No benches to show. Go ahead, add a new one 🚀
		</div>
		<div class="py-2" v-for="(bench, index) in benches" :key="bench.name">
			<div class="flex items-center justify-between">
				<router-link
					:to="`/benches/${bench.name}/overview`"
					class="mr-1 block w-full rounded-md py-2 hover:bg-gray-50 sm:px-2"
				>
					<div class="flex items-center justify-between">
						<div class="text-base w-2/3 sm:w-4/12">
							{{ bench.title }}
						</div>
						<div class="text-base w-1/3 sm:w-4/12">
							<Badge :label="bench.status" />
						</div>
						<div class="text-base hidden sm:block sm:w-4/12">
							<Badge
								:label="`${bench.number_of_apps} ${
									bench.number_of_apps == 1 ? 'App' : 'Apps'
								}`"
							/>
						</div>
						<div
							class="hidden w-2/12 text-right text-sm text-gray-600 sm:block"
						>
							{{ bench.version }} &middot; {{ bench.number_of_sites }} Sites
						</div>
					</div>
				</router-link>

				<div class="text-right text-base">
					<Dropdown :options="dropdownItems(bench)" right>
						<template v-slot="{ open }">
							<Button icon="more-horizontal" />
						</template>
					</Dropdown>
				</div>
			</div>
			<div
				class="translate-y-2 transform"
				:class="{ 'border-b': index < benches.length - 1 }"
			/>
		</div>
	</div>
</template>
<script>
export default {
	name: 'BenchList',
	props: ['benches'],
	methods: {
		benchBadge(bench) {
			let status = bench.status;
			let color = null;

			return {
				color,
				status
			};
		},
		dropdownItems(bench) {
			return [
				{
					label: 'New Site',
					onClick: () => {
						this.$router.push(`/${bench.name}/new`);
					}
				},
				{
					label: 'View Versions',
					onClick: () => {
						this.$router.push(`/benches/${bench.name}/versions`);
					}
				}
			];
		}
	}
};
</script>
