<template>
	<Card
		title="Regions"
		subtitle="Regions available for your bench"
		:loading="$resources.regions.loading"
	>
		<template #actions>
			<Button
				v-if="showAddRegionButton"
				@click="
					!$resources.availableRegions.data
						? $resources.availableRegions.fetch()
						: null;
					showAddRegionDialog = true;
				"
			>
				Add Region
			</Button>
		</template>

		<div class="divide-y">
			<ListItem
				v-for="region in $resources.regions.data"
				:key="region.name"
				:title="region.title"
				:image="region.image"
			>
			</ListItem>
		</div>

		<Dialog
			:options="{ title: 'Select secondary region for your bench' }"
			v-model="showAddRegionDialog"
		>
			<template v-slot:body-content>
				<LoadingText class="py-2" v-if="$resources.availableRegions.loading" />

				<RichSelect
					:value="selectedRegion"
					@change="selectedRegion = $event"
					:options="regionOptions"
				/>
			</template>

			<template #actions>
				<Button
					variant="solid"
					class="w-full"
					v-if="selectedRegion"
					:loading="$resources.addRegion.loading"
					@click="
						$resources.addRegion.submit({
							name: benchName,
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
	name: 'BenchRegions',
	props: ['benchName'],
	components: { RichSelect },
	data() {
		return {
			selectedRegion: null,
			showAddRegionDialog: false
		};
	},
	resources: {
		regions() {
			return {
				url: 'press.api.bench.regions',
				params: {
					name: this.benchName
				},
				auto: true
			};
		},
		availableRegions() {
			return {
				url: 'press.api.bench.available_regions',
				params: {
					name: this.benchName
				},
				auto: true,
				onSuccess(availableRegions) {
					if (availableRegions.length)
						this.selectedRegion = availableRegions[0].name;
				}
			};
		},
		addRegion() {
			return {
				url: 'press.api.bench.add_region',
				onSuccess() {
					window.location.reload();
				}
			};
		}
	},
	computed: {
		regionOptions() {
			let availableRegions = this.$resources.availableRegions.data;
			return availableRegions
				? availableRegions.map(d => ({
						label: d.title,
						value: d.name,
						image: d.image,
						beta: d.beta
				  }))
				: [];
		},
		showAddRegionButton() {
			let regions = this.$resources.regions.data;
			return regions && regions.length < 2;
		}
	}
};
</script>
