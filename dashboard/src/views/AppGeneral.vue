<template>
	<div>
		<Section
			title="App information"
			description="General information about your app"
		>
			<SectionCard>
				<DescriptionList
					class="px-6 py-4"
					:items="[
						{
							label: 'App Name',
							value: app.scrubbed
						},
						{
							label: 'Repository',
							value: app.repo_owner + '/' + app.repo
						},
						{
							label: 'Branch',
							value: app.branch
						},
						{
							label: 'Created On',
							value: formatDate(app.creation)
						},
						{
							label: 'Last Updated',
							value: formatDate(app.last_updated)
						}
					]"
				/>
			</SectionCard>
		</Section>
		<Section
			class="mt-10"
			title="Installed apps"
			description="Apps installed on your app"
		>
			<SectionCard>
				<a
					class="block px-6 py-3 hover:bg-gray-50"
					v-for="app in app.installed_apps"
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
	</div>
</template>

<script>
import DescriptionList from '@/components/DescriptionList';

export default {
	name: 'AppGeneral',
	props: ['app'],
	components: {
		DescriptionList
	}
};
</script>
