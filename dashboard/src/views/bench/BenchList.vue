<template>
	<div>
		<div
			class="py-2 text-base text-gray-600 sm:px-2"
			v-if="benches.length === 0"
		>
			No benches to show. Go ahead, create a new one 🚀
		</div>
		<div
			v-else
			class="rounded-md hover:bg-gray-50"
			v-for="(bench, index) in benches"
			:key="bench.name"
		>
			<div class="flex items-center">
				<div class="flex w-full items-center justify-between">
					<router-link
						:to="`/benches/${bench.name}/overview`"
						class="mr-1 block w-full px-3 py-4"
					>
						<div class="flex items-center justify-between">
							<div class="w-1/3 text-base font-medium">
								{{ bench.title }}
							</div>
							<div class="w-1/3 text-base">
								<Badge :label="bench.status" />
							</div>
							<div class="hidden w-4/12 text-base sm:block">
								<Badge :label="bench.version" />
							</div>
							<div class="mt-1 hidden w-1/6 text-sm text-gray-600 sm:block">
								{{
									`${bench.number_of_sites} ${$plural(
										bench.number_of_sites,
										'Site',
										'Sites'
									)}`
								}}
								&middot;
								{{
									`${bench.number_of_apps} ${$plural(
										bench.number_of_apps,
										'App',
										'Apps'
									)}`
								}}
							</div>
						</div>
					</router-link>
				</div>
				<Dropdown class="mr-2" :options="dropdownItems(bench)">
					<template v-slot="{ open }">
						<Button variant="ghost" icon="more-horizontal" />
					</template>
				</Dropdown>
			</div>
			<div v-if="index < benches.length - 1" class="mx-2.5 border-b" />
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
