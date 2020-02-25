<template>
	<div class="pb-16">
		<section>
			<h2 class="font-medium text-lg">Site information</h2>
			<p class="text-gray-600">General information about your site</p>
			<div class="w-1/2 mt-6 border border-gray-100 shadow rounded px-6 py-4">
				<div class="flex py-1">
					<div class="w-56 text-gray-800">Site name:</div>
					<div class="font-medium">{{ site.name }}</div>
				</div>
				<div class="flex py-1">
					<div class="w-56 text-gray-800">Created:</div>
					<div class="font-medium">
						<FormatDate>{{ site.creation }}</FormatDate>
					</div>
				</div>
				<div class="flex py-1">
					<div class="w-56 text-gray-800">Last update:</div>
					<div class="font-medium">
						<FormatDate>{{ site.last_updated }}</FormatDate>
					</div>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Installed apps</h2>
			<p class="text-gray-600">Apps installed on your site</p>
			<div class="w-1/2 mt-6 border border-gray-100 shadow rounded px-6 py-4">
				<div class="py-2" v-for="app in site.installed_apps">
					<p>
						<a
							:href="`${app.url}/tree/${app.branch}`"
							class="font-medium text-brand"
						>
							{{ app.owner }}/{{ app.repo }}
						</a>
					</p>
					<p class="text-sm text-gray-800">
						{{ app.branch }}
					</p>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Activity</h2>
			<p class="text-gray-600">Activities performed on your site</p>
			<div class="w-1/2 mt-6 border border-gray-100 shadow rounded px-6 py-4">
				<div class="py-3" v-for="a in activities">
					<div>
						{{ a.text }}  <span class="text-gray-800">by {{ a.owner }}</span>
					</div>
					<div class="text-sm text-gray-600">
						<FormatDate>
							{{ a.creation }}
						</FormatDate>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
export default {
	name: 'SiteGeneral',
	props: ['site'],
	data() {
		return {
			activities: []
		};
	},
	mounted() {
		this.fetchActivities();
	},
	methods: {
		async fetchActivities() {
			let activities = await this.$call('frappe.client.get_list', {
				doctype: 'Site History',
				fields: 'action, creation, owner',
				filters: { site: this.site.name }
			});

			this.activities = activities.map(d => {
				let text = {
					Create: 'Site created'
				}[d.action] || d.action;
				return {
					...d,
					text
				};
			});
		}
	}
};
</script>
