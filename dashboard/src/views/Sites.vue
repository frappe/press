<template>
	<div>
		<PageHeader>
			<h1 slot="title">Sites</h1>
			<div class="flex items-center" slot="actions">
				<Button
					v-if="$store.sites.all.length"
					route="/sites/new"
					type="primary"
				>
					<FeatherIcon name="plus" class="w-4 h-4" />
					<span class="ml-1">
						New Site
					</span>
				</Button>
				<SearchBar class="hidden ml-4 sm:block" />
			</div>
		</PageHeader>
		<div class="px-4 sm:px-8">
			<div class="mb-5 border-t"></div>
			<div
				v-if="$store.sites.all.length"
				class="grid grid-cols-1 gap-4 mb-16 sm:grid-cols-3"
			>
				<router-link
					:to="`/sites/${site.name}`"
					v-for="site in $store.sites.all"
					:key="site.name"
				>
					<div class="p-4 border rounded-md shadow hover:shadow-md">
						<div class="flex items-baseline justify-between">
							<span>
								{{ site.name }}
							</span>
							<Badge :status="site.status">
								{{ site.status }}
							</Badge>
						</div>
						<div class="mt-2 text-sm text-gray-600">
							Last updated
							<FormatDate type="relative">{{ site.modified }}</FormatDate>
						</div>
					</div>
				</router-link>
			</div>
			<div
				class="p-24 text-center"
				v-if="$store.sites.fetched && $store.sites.all.length === 0"
			>
				<div class="text-gray-800">
					You haven't created any sites yet.
				</div>
				<Button route="/sites/new" class="mt-10" type="primary">
					Create your first Site
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Sites',
	mounted() {
		this.$store.sites.fetchAll();
		this.$store.sites.setupSocketListener();
	},
	methods: {
		relativeDate(dateString) {
			return dateString;
		}
	}
};
</script>
