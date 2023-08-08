<template>
	<router-link
		:to="{ name: 'SiteOverview', params: { siteName: site.name } }"
		class="rounded px-3 py-3 hover:bg-gray-100"
	>
		<div class="flex items-center">
			<div class="w-4/12">
				<div class="flex items-center space-x-2">
					<div class="truncate text-base font-medium" :title="site.name">
						{{ site.name }}
					</div>
				</div>
				<div class="mt-1 hidden text-base text-gray-600 sm:block">
					Created on {{ formatDate(site.creation, 'DATE_MED') }}
				</div>
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
					class="h-4"
					:src="site.server_region_info.image"
					:alt="`Flag of ${site.server_region_info.title}`"
					:title="site.server_region_info.image"
				/>
			</div>
			<div class="w-1/12">
				<div class="text-base text-gray-700">
					{{ site.plan ? `${$planTitle(site.plan)}/mo` : 'No Plan Set' }}
				</div>
			</div>

			<div class="ml-auto flex items-center">
				<Dropdown :options="dropdownItems(site)">
					<template v-slot="{ open }">
						<Button variant="ghost" class="ml-2" icon="more-horizontal" />
					</template>
				</Dropdown>
			</div>
		</div>
	</router-link>
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
