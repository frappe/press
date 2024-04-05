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
							scheduled_datetime: datetimeInIST,
							skip_failing_patches: skipFailingPatches
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
			<div v-else class="space-y-4">
				<FormControl
					variant="outline"
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
				<div
					class="space-y-4"
					v-if="
						$resources.changeRegionOptions.data?.regions?.length > 0 &&
						selectedRegion
					"
				>
					<DateTimeControl v-model="targetDateTime" label="Schedule Time" />
					<FormControl
						label="Skip failing patches if any"
						type="checkbox"
						v-model="skipFailingPatches"
					/>
				</div>
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
import DateTimeControl from '../../../src2/components/DateTimeControl.vue';

export default {
	name: 'SiteChangeRegionDialog',
	props: ['site', 'modelValue'],
	emits: ['update:modelValue'],
	components: {
		DateTimeControl
	},
	data() {
		return {
			targetDateTime: null,
			selectedRegion: null,
			skipFailingPatches: false
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
				.tz('Asia/Kolkata')
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
