<template>
	<Dialog
		:options="{
			title: 'Change Region'
		}"
		v-model="show"
		@close="resetValues"
	>
		<template #body-content>
			<LoadingIndicator
				class="mx-auto h-4 w-4"
				v-if="$resources.changeRegionOptions.loading"
			/>
			<p
				v-else-if="$resources.changeRegionOptions.data.regions.length < 2"
				class="text-base text-gray-600"
			>
				You have only one region available. Add more regions to the current
				bench from bench settings to change the region of this site.
			</p>
			<div v-else>
				<RichSelect
					:value="selectedRegion"
					@change="selectedRegion = $event"
					:options="
						$resources.changeRegionOptions.data.regions.map(r => ({
							label: r.title || r.name,
							value: r.name,
							image: r.image
						}))
					"
				/>
				<FormControl
					class="mt-4"
					v-if="$resources.changeRegionOptions.data?.regions?.length > 0"
					label="Schedule Site Migration (IST)"
					type="datetime-local"
					:min="new Date().toISOString().slice(0, 16)"
					v-model="targetDateTime"
				/>
				<p class="mt-4 text-sm text-gray-500">
					Changing region may cause a downtime between 30 minutes to 1 hour
				</p>
			</div>
			<ErrorMessage class="mt-3" :message="$resources.changeRegion.error" />
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				:disabled="
					$resources.changeRegionOptions?.data &&
					$resources.changeRegionOptions.data.regions.length < 2
				"
				:loading="$resources.changeRegion.loading"
				@click="
					$resources.changeRegion.submit({
						name: site?.name,
						cluster: selectedRegion,
						scheduled_datetime: targetDateTime
					})
				"
			>
				Submit
			</Button>
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';
import RichSelect from '@/components/RichSelect.vue';

export default {
	name: 'SiteChangeRegionDialog',
	props: ['site', 'modelValue'],
	emits: ['update:modelValue'],
	components: {
		RichSelect
	},
	data() {
		return {
			targetDateTime: null,
			selectedRegion: null
		};
	},
	watch: {
		show(value) {
			if (value) this.$resources.changeRegionOptions.fetch();
		}
	},
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	},
	resources: {
		changeRegionOptions() {
			return {
				url: 'press.api.site.change_region_options',
				params: {
					name: this.site?.name
				},
				onSuccess(data) {
					this.selectedRegion = data.current_region;
				}
			};
		},
		changeRegion() {
			return {
				url: 'press.api.site.change_region',
				params: {
					name: this.site?.name,
					cluster: this.selectedRegion
				},
				validate() {
					if (
						this.$resources.changeRegionOptions.data.current_region ===
						this.selectedRegion
					)
						return 'Site is already in this region';
				},
				onSuccess() {
					const regionName =
						this.$resources.changeRegionOptions.data.regions.find(
							region => region.name === this.selectedRegion
						)?.title || this.selectedRegion;

					notify({
						title: 'Scheduled Region Change',
						message: `Site scheduled to be moved to ${regionName}`,
						color: 'green',
						icon: 'check'
					});
					this.$emit('update:modelValue', false);
				}
			};
		}
	},
	methods: {
		resetValues() {
			this.selectedRegion = null;
			this.targetDateTime = null;
		}
	}
};
</script>
