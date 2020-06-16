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
			title="Compatible Versions"
			description="Versions compatible with your app"
		>
			<SectionCard>
				<div
					class="block px-6 py-3 hover:bg-gray-50"
					v-for="group in app.groups"
					:key="group.name"
				>
					<p class="text-base font-medium text-brand">
						{{ group.name }}
					</p>
					<p class="text-sm text-gray-800">
						{{ group.frappe.scrubbed }}/{{ group.frappe.branch }}
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
