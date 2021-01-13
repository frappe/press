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
			v-if="bench.status == 'Active' && bench.update_available"
			class="mt-10"
			title="Update Available"
			description="Deploy most recent version of your bench"
		>
			<Button
				type="secondary"
				@click="$resources.deploy.fetch()"
				:disabled="$resources.deploy.loading"
			>
				Deploy now
			</Button>
		</Section>
		<Section
			v-if="bench.status == 'Awaiting Deploy' && bench.update_available"
			class="mt-10"
			title="Deploy"
			description="Deploy first version of your bench"
		>
			<Button
				type="primary"
				@click="$resources.deploy.fetch()"
				:disabled="$resources.deploy.loading"
			>
				Deploy now
			</Button>
		</Section>
		<Section
			v-if="bench.status == 'Active'"
			class="mt-10"
			title="New Site"
			description="Create New Site on your Bench"
		>
			<Button type="primary" :route="'/sites/new?bench=' + this.bench.name">
				New Site
			</Button>
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
	resources: {
		deploy() {
			return {
				method: 'press.api.bench.deploy',
				params: {
					name: this.bench.name
				},
				onSuccess(candidate) {
					this.$router.push(`/benches/${this.bench.name}/deploys/${candidate}`);
				}
			};
		}
	}
};
</script>
