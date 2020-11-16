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
							value: app.name
						},
						{
							label: 'Installations',
							value: app.installations
						},
						{
							label: 'Created',
							value: formatDate(app.creation)
						},
						{
							label: 'Last Updated',
							value: formatDate(app.modified)
						}
					]"
				/>
			</SectionCard>
		</Section>
		<Section
			class="mt-10"
			title="Compatible Versions"
			description="Versions compatible with your app"
		>
			<SectionCard>
				<div
					class="block px-6 py-3 hover:bg-gray-50"
					v-for="version in app.versions"
					:key="version.name"
				>
					<p class="text-base font-medium text-brand">
						{{ version.name }}
					</p>
				</div>
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
