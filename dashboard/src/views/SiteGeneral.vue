<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Site information</h2>
			<p class="text-gray-600">General information about your site</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-2"
			>
				<div class="grid grid-cols-3 py-3 px-6 text-sm">
					<div class="text-gray-700 font-medium">Site name:</div>
					<div class="col-span-2 font-medium">{{ site.name }}</div>
				</div>
				<div class="grid grid-cols-3 py-3 border-t px-6 text-sm">
					<div class="text-gray-700 font-medium">Created:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ site.creation }}</FormatDate>
					</div>
				</div>
				<div class="grid grid-cols-3 py-3 border-t px-6 text-sm">
					<div class="text-gray-700 font-medium">Last update:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ site.last_updated }}</FormatDate>
					</div>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Installed apps</h2>
			<p class="text-gray-600">Apps installed on your site</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-4"
			>
				<a
					class="px-6 py-2 block hover:bg-gray-50"
					v-for="app in site.installed_apps"
					:href="`${app.url}/tree/${app.branch}`"
					target="_blank"
				>
					<p class="font-medium text-brand">{{ app.owner }}/{{ app.repo }}</p>
					<p class="text-sm text-gray-800">
						{{ app.branch }}
					</p>
				</a>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="font-medium text-lg">Activity</h2>
			<p class="text-gray-600">Activities performed on your site</p>
			<div
				class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-4"
			>
				<div class="px-6 py-3 hover:bg-gray-50" v-for="a in activities">
					<div>
						{{ a.text }} <span class="text-gray-800">by {{ a.owner }}</span>
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
			let activities = await this.$call('press.api.site.activities', {
				name: this.site.name
			});

			this.activities = activities.map(d => {
				let text =
					{
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
