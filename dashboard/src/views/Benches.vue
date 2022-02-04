<template>
	<div class="pt-4">
		<PageHeader>
			<h1 slot="title">Benches</h1>
			<div class="flex items-center" slot="actions">
				<Button route="/benches/new" type="primary" iconLeft="plus">
					New Bench
				</Button>
			</div>
		</PageHeader>
		<div class="px-4 sm:px-8">
			<div
				class="p-24 text-center"
				v-if="$resources.benches.data && $resources.benches.data.length === 0"
			>
				<div class="text-xl text-gray-800">
					You haven't created any benches yet.
				</div>
				<Button route="/benches/new" class="mt-10" type="primary">
					Create your first Bench
				</Button>
			</div>
			<div v-else>
				<div
					class="grid grid-cols-2 items-center gap-12 border-b py-4 text-sm text-gray-600 md:grid-cols-4"
				>
					<span>Bench Name</span>
					<span class="text-right md:text-center">Status</span>
					<span class="hidden text-right md:inline">Active Since</span>
					<span class="hidden md:inline"></span>
				</div>
				<router-link
					class="focus:shadow-outline grid grid-cols-2 items-center gap-12 border-b py-4 text-base hover:bg-gray-50 focus:outline-none md:grid-cols-4"
					v-for="bench in $resources.benches.data"
					:key="bench.name"
					:to="'/benches/' + bench.name"
				>
					<span class="">{{ bench.title }}</span>
					<span class="text-right md:text-center">
						<Badge :status="bench.status" />
					</span>
					<FormatDate class="hidden text-right md:block" type="relative">
						{{ bench.creation }}
					</FormatDate>
					<span class="hidden text-right md:inline">
						<Badge
							v-if="
								(bench.status === 'Active' ||
									bench.status === 'Inactive' ||
									bench.status === 'Suspended') &&
								bench.update_available
							"
							:status="'Update Available'"
							class="mr-4"
						/>
					</span>
				</router-link>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Benches',
	resources: {
		benches: 'press.api.bench.all'
	}
};
</script>
