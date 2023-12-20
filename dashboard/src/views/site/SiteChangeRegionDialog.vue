<template>
	<Dialog
		:options="{
			title: 'Change Region',
			actions: [
				{
					label: 'Add Region to Bench',
					loading: $resources.addRegionToReleaseGroup.loading,
					disabled:
						!selectedRegion ||
						site?.is_public ||
						$resources.changeRegionOptions.data.group_regions.includes(
							selectedRegion
						),
					onClick: () => $resources.addRegionToReleaseGroup.submit()
				},
				{
					label: 'Change Region',
					loading: $resources.changeRegion.loading,
					variant: 'solid',
					disabled:
						!selectedRegion ||
						!$resources.changeRegionOptions.data.group_regions.includes(
							selectedRegion
						),
					onClick: () =>
						$resources.changeRegion.submit({
							name: site?.name,
							cluster: selectedRegion,
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
				<RichSelect
					:value="selectedRegion"
					@change="selectedRegion = $event"
					:options="
						$resources.changeRegionOptions.data.regions.map(r => ({
							label: r.title || r.name,
							value: r.name,
							image: r.image,
							beta: r.beta
						}))
					"
				/>
				<FormControl
					class="mt-4"
					v-if="
						$resources.changeRegionOptions.data?.regions?.length > 0 &&
						selectedRegion &&
						$resources.changeRegionOptions.data.group_regions.includes(
							selectedRegion
						)
					"
					label="Schedule Site Migration"
					type="datetime-local"
					:min="new Date().toISOString().slice(0, 16)"
					v-model="targetDateTime"
				/>
				<p class="mt-4 text-sm text-gray-600">
					{{ message }}
				</p>
			</div>
			<ErrorMessage class="mt-3" :message="$resources.changeRegion.error" />
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
		},
		message() {
			if (
				this.$resources.changeRegionOptions.data.group_regions.includes(
					this.selectedRegion
				)
			) {
				return 'Selected region is available in the bench. You can schedule the site migration to this region.';
			} else if (
				!this.$resources.changeRegionOptions.data.group_regions.includes(
					this.selectedRegion
				)
			) {
				if (this.site?.is_public)
					return 'Selected region is not available in the bench. Get in touch with support to add this region.';
				else
					return 'Selected region is not available in the bench. You can add this region to the bench and then schedule the site migration later.';
			} else return '';
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
				onSuccess(data) {
					if (data.regions.find(r => r.name === data.current_region))
						this.selectedRegion = data.current_region;
				}
			};
		},
		addRegionToReleaseGroup() {
			return {
				url: 'press.api.site.add_region_to_group',
				params: {
					name: this.site?.group,
					region: this.selectedRegion
				},
				validate() {
					if (
						this.$resources.changeRegionOptions.data.group_regions.includes(
							this.selectedRegion
						)
					)
						return 'Region is already added to the release group';
				},
				onSuccess(data) {
					notify({
						title: 'Region Added to Release Group',
						message: `Please wait till the deploy in the region ${this.selectedRegion} is done.`,
						color: 'green',
						icon: 'check'
					});
					this.$emit('update:modelValue', false);
					this.$router.push({
						name: 'BenchDeploys',
						params: {
							benchName: this.site?.group,
							candidateName: data
						}
					});
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
