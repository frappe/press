<template>
	<div>
		<Section
			title="Bench information"
			description="General information about your bench"
		>
			<SectionCard>
				<DescriptionList
					class="px-6 py-4"
					:items="[
						{
							label: 'Bench Name',
							value: bench.name
						},
						{
							label: 'Version',
							value: bench.version
						},
						{
							label: 'Created On',
							value: formatDate(bench.creation)
						},
						{
							label: 'Last Updated',
							value: formatDate(bench.last_updated)
						}
					]"
				/>
			</SectionCard>
		</Section>
		<Section
			v-if="bench.update_available"
			class="mt-10"
			title="Update Available"
			description="Deploy most recent version of your bench"
		>
		</Section>
	</div>
</template>

<script>
import DescriptionList from '@/components/DescriptionList';

export default {
	name: 'BenchGeneral',
	props: ['bench'],
	components: {
		DescriptionList
	},
	resources: {}
};
</script>
