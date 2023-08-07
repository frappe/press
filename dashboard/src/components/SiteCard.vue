<template>
	<router-link
		:to="{ name: 'SiteOverview', params: { siteName: site.name } }"
		class="rounded-md border border-gray-200 p-3 hover:border-gray-300"
	>
		<div class="space-y-2">
			<div class="flex items-center justify-center">
				<div class="w-full truncate text-lg mr-2" :title="site.name">
					{{ site.name }}
				</div>
				<div>
					<a :href="`http://${site.name}`" target="_blank" @click.stop>
						<FeatherIcon class="h-4 w-4" name="external-link" />
					</a>
				</div>
				<Dropdown
					v-if="site.status === 'Active' || site.status === 'Updating'"
					:options="dropdownItems(site)"
				>
					<template v-slot="{ open }">
						<Button variant="ghost" class="ml-2" icon="more-horizontal" />
					</template>
				</Dropdown>
			</div>
			<div class="flex items-center space-x-3">
				<Badge :label="site.version" />
				<Badge
					class="pointer-events-none"
					variant="subtle"
					:label="siteBadge(site)"
				/>
				<img
					v-if="site.server_region_info?.image"
					class="h-4"
					:src="site.server_region_info.image"
					:alt="`Flag of ${site.server_region_info.title}`"
					:title="site.server_region_info.image"
				/>
			</div>
			<div class="hidden text-sm text-gray-600 sm:block">
				{{ $dayjs(site.creation).fromNow() }}
			</div>
		</div>
	</router-link>
</template>

<script>
export default {
	name: 'SiteCard',
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
