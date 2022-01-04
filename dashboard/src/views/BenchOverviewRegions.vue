<template>
	<Card
		title="Regions"
		subtitle="Regions available for your bench"
		:loading="regions.loading"
	>
		<template #actions>
			<Button
				@click="
					!availableRegions.data ? availableRegions.fetch() : null;
					showAddRegionDialog = true;
				"
			>
				Add Region
			</Button>
		</template>

		<div class="divide-y">
			<ListItem
				v-for="region in regions.data"
				:key="region.name"
				:title="region.title"
			>
				<!-- TODO: Add image<24-12-21, Balamurali M> -->
			</ListItem>
		</div>

		<Dialog
			title="Select secondary region for your bench"
			v-model="showAddRegionDialog"
		>
			<Loading class="py-2" v-if="availableRegions.loading" />

			<RichSelect
				:value="selectedRegion"
				:options="regionOptions"
			/>
			<template #actions>
				<Button
					type="primary"
					v-if="selectedRegion"
					:loading="addRegion.loading"
					@click="
						addRegion.submit({
							name: bench.name,
							region: selectedRegion
						})
					"
				>
					Add
				</Button>
			</template>
		</Dialog>
	</Card>
</template>

<script>
import RichSelect from '@/components/RichSelect.vue';

export default {
	name: 'BenchOverviewRegions',
	props: ['bench'],
	components: { RichSelect },
	data() {
		return {
			selectedRegion: null,
			showAddRegionDialog: false,
		};
	},
	resources: {
		regions() {
			return {
				method: 'press.api.bench.regions',
				params: {
					name: this.bench.name,
				},
				auto: true,
			};
		},
		availableRegions() {
			return {
				method: 'press.api.bench.available_regions',
				params: {
					name: this.bench.name,
				},
				auto: true,
				onSuccess(availableRegions) {
					this.selectedRegion = availableRegions[0].name;
				}
			};
		},
		addRegion() {
			return {
				method: 'press.api.bench.add_region',
				params: {
					name: this.bench.name,
					region: this.selectedRegion,
				},
				onSuccess() {
					window.location.reload();
				},
			};
		},
		removeRegion() {
			return {
				method: 'press.api.bench.remove_region',
			};
		},
	},
	methods: {
		dropdownItems(region) {
			return [
				{
					label: 'Remove Region',
					action: () => this.confirmRemoveRegion(region),
					//condition: () => region.name != 'frregione'
					// TODO convert above condition to more than 1 region
				},
			].filter(Boolean);
		},

		confirmRemoveRegion(region) {
			this.$confirm({
				title: 'Remove Region',
				message: `Are you sure you want to remove region ${region.name} from this bench?`,
				actionLabel: 'Remove Region',
				actionType: 'danger',
				resource: this.$resources.removeRegion,
				action: (_) => {
					this.$resources.removeRegion.submit({
						name: this.bench.name,
						region: region.name,
					});
				},
			});
		},
	},
	computed: {
		regionOptions() {
			let regions = this.$resources.availableRegions.data;
			return regions
				? regions.map((d) => ({
						label: d.title,
						value: d.name,
						image: d.image,
				  }))
				: [];
		},
	},
};
</script>
