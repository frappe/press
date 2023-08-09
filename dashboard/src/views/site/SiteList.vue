<template>
	<div class="flex items-center rounded hover:bg-gray-100">
		<router-link
			:to="{ name: 'SiteOverview', params: { siteName: site.name } }"
			class="w-full px-3 py-4"
		>
			<div class="flex items-center">
				<div class="w-4/12 truncate text-base font-medium" :title="site.name">
					{{ site.name }}
				</div>
				<div class="w-2/12">
					<Badge
						class="pointer-events-none"
						variant="subtle"
						:label="siteBadge(site)"
					/>
				</div>
				<div class="w-2/12">
					<img
						v-if="site.server_region_info.image"
						class="h-4"
						:src="site.server_region_info.image"
						:alt="`Flag of ${site.server_region_info.title}`"
						:title="site.server_region_info.image"
					/>
					<span class="text-base text-gray-700" v-else>
						{{ site.server_region_info.title }}
					</span>
				</div>
				<div class="w-1/12">
					<div class="text-base text-gray-700">
						{{ site.plan ? `${$planTitle(site.plan)}/mo` : 'No Plan Set' }}
					</div>
				</div>
			</div>
		</router-link>
		<Dropdown :options="dropdownItems(site)">
			<template v-slot="{ open }">
				<Button variant="ghost" class="mr-2" icon="more-horizontal" />
			</template>
		</Dropdown>
	</div>
</template>

<script>
export default {
	name: 'SiteList',
	props: {
		site: {
			type: Object,
			required: true
		},
		dropdownItems: {
			type: Function,
			required: true
		}
	},
	methods: {
		siteBadge(site) {
			let status = site.status;
			if (site.update_available && site.status == 'Active') {
				status = 'Update Available';
			}

			let usage = Math.max(
				site.current_cpu_usage,
				site.current_database_usage,
				site.current_disk_usage
			);
			if (usage && usage >= 80 && status == 'Active') {
				status = 'Attention Required';
			}
			if (site.trial_end_date) {
				status = 'Trial';
			}
			return status;
		}
	}
};
</script>
