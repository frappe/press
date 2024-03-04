<template>
	<Dialog
		:options="{
			title: 'Change Region',
			actions: [
				{
					label: 'Change Region',
					loading: $resources.changeRegion.loading,
					variant: 'solid',
					disabled: !selectedRegion,
					onClick: () =>
						$resources.changeRegion.submit({
							name: site?.name,
							cluster: selectedRegion?.value,
							scheduled_datetime: datetimeInIST
						})
				}
			]
		}"
		v-model="show"
		@close="resetValues"
	>
		<template #body-content>
			<LoadingIndicator
				class="mx-auto h-4 w-4"
				v-if="$resources.changeRegionOptions.loading"
			/>
			<div v-else>
				<FormControl
					type="autocomplete"
					label="Choose Region"
					v-model="selectedRegion"
					:options="
						$resources.changeRegionOptions.data.regions.map(r => ({
							label: r.title || r.name,
							value: r.name,
							image: r.image
						}))
					"
				>
					<template #prefix>
						<img :src="selectedRegion?.image" class="mr-2 h-4" />
					</template>
					<template #item-prefix="{ active, selected, option }">
						<img v-if="option?.image" :src="option.image" class="mr-2 h-4" />
					</template>
				</FormControl>
				<FormControl
					class="mt-4"
					v-if="
						$resources.changeRegionOptions.data?.regions?.length > 0 &&
						selectedRegion
					"
					label="Schedule Site Migration"
					type="datetime-local"
					:min="new Date().toISOString().slice(0, 16)"
					v-model="targetDateTime"
				/>
				<p v-else class="mt-4 text-sm text-gray-600">
					If the region you're looking for isn't available, please add from the
					Bench dashboard.
				</p>
			</div>
			<ErrorMessage class="mt-3" :message="$resources.changeRegion.error" />
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	name: 'SiteChangeRegionDialog',
	props: ['site', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			targetDateTime: null,
			selectedRegion: null
		};
	},
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime)
				.tz('Asia/Tokyo')
				.format('YYYY-MM-DDTHH:mm');

			return datetimeInIST;
		}
	},
	resources: {
		changeRegionOptions() {
			return {
				url: 'press.api.site.change_region_options',
				params: {
					name: this.site?.name
				},
				auto: true
			};
		},
		changeRegion() {
			return {
				url: 'press.api.site.change_region',
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
						message: `Site <b>${this.site?.host_name}</b> scheduled to be moved to <b>${regionName}</b>`,
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
