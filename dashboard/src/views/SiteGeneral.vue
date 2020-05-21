<template>
	<div>
		<Section
			title="Site information"
			description="General information about your site"
		>
			<SectionCard>
				<div class="grid grid-cols-3 px-6 py-3 text-sm">
					<div class="font-medium text-gray-700">Site name:</div>
					<div class="col-span-2 font-medium">{{ site.name }}</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-sm border-t">
					<div class="font-medium text-gray-700">Created:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ site.creation }}</FormatDate>
					</div>
				</div>
				<div class="grid grid-cols-3 px-6 py-3 text-sm border-t">
					<div class="font-medium text-gray-700">Last update:</div>
					<div class="col-span-2 font-medium">
						<FormatDate>{{ site.last_updated }}</FormatDate>
					</div>
				</div>
			</SectionCard>
		</Section>
		<Section
			v-if="site.status === 'Active' && site.update_available"
			class="mt-10"
			title="Update Available"
			description="Schedule an update for your site"
		>
			<Button
				@click="$resources.scheduleUpdate.fetch()"
				:disabled="$resources.scheduleUpdate.loading"
				type="primary"
			>
				Schedule Update
			</Button>
		</Section>
		<Section
			class="mt-10"
			title="Installed apps"
			description="Apps installed on your site"
		>
			<SectionCard>
				<a
					class="block px-6 py-3 hover:bg-gray-50"
					v-for="app in site.installed_apps"
					:href="`${app.url}/tree/${app.branch}`"
					:key="app.url"
					target="_blank"
				>
					<p class="font-medium text-brand">{{ app.owner }}/{{ app.repo }}</p>
					<p class="text-sm text-gray-800">
						{{ app.branch }}
					</p>
				</a>
			</SectionCard>
		</Section>
		<Section
			v-if="site.status === 'Active'"
			class="mt-10"
			title="Login"
			description="Login directly to your site as Administrator"
		>
			<Button
				@click="$resources.loginAsAdministrator.fetch()"
				:disabled="$resources.loginAsAdministrator.loading"
			>
				Login as Administrator
			</Button>
		</Section>
		<SiteDrop class="mt-10" :site="site" />
	</div>
</template>

<script>
import SiteDrop from './SiteDrop.vue';

export default {
	name: 'SiteGeneral',
	props: ['site'],
	components: {
		SiteDrop
	},
	resources: {
		loginAsAdministrator() {
			return {
				method: 'press.api.site.login',
				params: {
					name: this.site.name
				},
				onSuccess(sid) {
					if (sid) {
						window.open(`https://${this.site.name}/desk?sid=${sid}`, '_blank');
					}
				}
			};
		},
		scheduleUpdate() {
			return {
				method: 'press.api.site.update',
				params: {
					name: this.site.name
				}
			};
		}
	}
};
</script>
