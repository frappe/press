<template>
	<div
		class="sm:py-1 sm:border sm:border-gray-100 sm:rounded-md sm:shadow sm:px-2"
	>
		<div class="py-2 text-base text-gray-600 sm:px-2" v-if="sites.length === 0">
			No sites in this bench
		</div>
		<div class="py-2" v-for="(site, index) in sites" :key="site.name">
			<div
				@click="routeToSite(site)"
				class="block pt-2 rounded-md sm:px-2 hover:bg-gray-50 cursor-pointer"
			>
				<div class="flex items-center justify-between sm:justify-start">
					<div class="text-base sm:w-4/12">
						{{ site.name }}
					</div>
					<div class="text-base sm:w-4/12">
						<Badge class="pointer-events-none" v-bind="siteBadge(site)" />
					</div>
					<div class="hidden w-2/12 text-sm text-gray-600 sm:block">
						Created {{ formatDate(site.creation, 'relative') }}
					</div>
					<div class="hidden w-2/12 text-base text-right sm:block">
						<Link
							v-if="site.status === 'Active' || site.status === 'Updating'"
							:to="`https://${site.name}`"
							target="_blank"
							class="inline-flex items-center text-sm"
							@click.stop
						>
							Visit Site
							<FeatherIcon name="external-link" class="w-3 h-3 ml-1" />
						</Link>
					</div>
				</div>
				<div
					class="pt-2 transform translate-y-2"
					:class="{ 'border-b': index < sites.length - 1 }"
				/>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'SiteList',
	props: ['sites'],
	methods: {
		siteBadge(site) {
			let status = site.status;
			let color = null;
			if (site.update_available && site.status == 'Active') {
				status = 'Update Available';
				color = 'blue';
			}

			let usage = Math.max(
				site.current_cpu_usage,
				site.current_database_usage,
				site.current_disk_usage
			);
			if (usage && usage >= 80 && status == 'Active') {
				status = 'Attention Required';
				color = 'yellow';
			}
			if (site.trial_end_date) {
				status = 'Trial';
				color = 'yellow';
			}
			return {
				color,
				status
			};
		},
		routeToSite(site) {
			let redirectPath = `dashboard/sites/${site.name}/database`;
			window.location.href = `/${redirectPath}`;
		}
	}
};
</script>
