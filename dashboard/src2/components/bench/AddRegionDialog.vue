<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Add Region',
			actions: [
				{
					label: 'Add Region',
					variant: 'solid',
					loading: groupDocResource.addRegion.loading,
					disabled: !selectedRegion,
					onClick: () =>
						groupDocResource.addRegion.submit({
							region: selectedRegion.value
						})
				}
			]
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					type="autocomplete"
					label="Choose Region"
					:options="regionOptions"
					v-model="selectedRegion"
				>
					<template #prefix>
						<img :src="selectedRegion?.image" class="mr-2 h-4" />
					</template>
					<template #item-prefix="{ active, selected, option }">
						<img v-if="option?.image" :src="option.image" class="mr-2 h-4" />
					</template>
				</FormControl>
				<ErrorMessage :message="groupDocResource.addRegion.error" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';

export default {
	name: 'AddRegionDialog',
	props: ['group'],
	data() {
		return {
			showDialog: true,
			selectedRegion: null,
			groupDocResource: getCachedDocumentResource('Release Group', this.group)
		};
	},
	computed: {
		regionOptions() {
			return this.$resources.availableRegions.data.map(r => ({
				label: r.title || r.name,
				value: r.name,
				image: r.image,
				beta: r.beta
			}));
		}
	},
	resources: {
		availableRegions() {
			return {
				url: 'press.api.bench.available_regions',
				params: {
					name: this.group
				},
				auto: true,
				initialData: []
			};
		}
	}
};
</script>
