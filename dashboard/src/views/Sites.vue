<template>
	<div>
		<PageHeader>
			<h1 slot="title">Sites</h1>
			<div class="flex items-center" slot="actions">
				<Button
					route="/sites/new"
					class="bg-brand text-white flex items-center pr-5 text-sm leading-none"
				>
					<FeatherIcon name="plus" class="w-4 h-4" />
					<span class="ml-1">
						New Site
					</span>
				</Button>
				<SearchBar class="ml-4 hidden sm:block" />
			</div>
		</PageHeader>
		<div class="px-4 sm:px-8">
			<div class="border-t mb-5"></div>
			<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-16">
				<router-link
					:to="`/sites/${site.name}`"
					v-for="site in sites"
					:key="site.name"
				>
					<div class="shadow border rounded-md p-4 hover:shadow-md">
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
		</div>
	</div>
</template>

<script>
export default {
	name: 'Sites',
	data: () => ({
		sites: []
	}),
	async mounted() {
		this.sites = await this.$call('frappe.client.get_list', {
			doctype: 'Site',
			fields: ['name, status, modified']
		});
	},
	methods: {
		relativeDate(dateString) {
			return dateString;
		}
	}
};
</script>
