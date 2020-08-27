<template>
	<div>
		<Section
			title="Site information"
			description="General information about your site"
		>
			<SectionCard>
				<DescriptionList
					class="px-6 py-4"
					:items="[
						{
							label: 'Created On',
							value: formatDate(site.creation)
						},
						{
							label: 'Last Updated',
							value: formatDate(site.last_updated)
						},
						{
							label: 'Created By',
							value: site.owner
						},
					]"
				/>
			</SectionCard>
		</Section>
		<Section
			v-if="
				(site.status === 'Active' ||
					site.status === 'Inactive' ||
					site.status === 'Suspended') &&
					site.update_available
			"
			class="mt-10"
			title="Update Available"
			description="Update your site now"
		>
			<Button
				@click="$resources.scheduleUpdate.fetch()"
				:disabled="$resources.scheduleUpdate.loading"
				type="primary"
			>
				Update now
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
					<p class="text-base font-medium text-brand">
						{{ app.owner }}/{{ app.repo }}
					</p>
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
		<SiteDrop class="mt-10" :site="site" v-if="site.status !== 'Pending'" />
	</div>
</template>

<script>
import SiteDrop from './SiteDrop.vue';
import DescriptionList from '@/components/DescriptionList';

export default {
	name: 'SiteGeneral',
	props: ['site'],
	components: {
		SiteDrop,
		DescriptionList
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
