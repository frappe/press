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
					onClick: changeRegion
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
				<p
					v-else-if="!$site.doc.group_public"
					class="mt-4 text-sm text-gray-600"
				>
					If the region you're looking for isn't available, please add from the
					Bench Group dashboard.
				</p>
				<div
					class="rounded border border-gray-200 bg-gray-100 p-2"
					v-if="$resources.ARecords.data?.length == 0"
				>
					<p class="text-sm text-gray-700">
						<strong>Note</strong>: This site seem to have custom domains with
						<strong>A record</strong>. Please update the same after migration to
						avoid downtime. To know more, refer
						<a
							href="https://frappecloud.com/docs/sites/custom-domains"
							target="_blank"
							class="underline"
							>the documentation.</a
						>
					</p>
				</div>
			</div>
			<ErrorMessage class="mt-3" :message="$resources.changeRegion.error" />
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import DateTimeControl from '../DateTimeControl.vue';

export default {
	props: ['site'],
	data() {
		return {
			show: true,
			targetDateTime: null,
			selectedRegion: null,
			skipFailingPatches: false
		};
	},
	components: {
		DateTimeControl
	},
	computed: {
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime)
				.tz('Asia/Kolkata')
				.format('YYYY-MM-DDTHH:mm');

			return datetimeInIST;
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	},
	resources: {
		ARecords() {
			return {
				type: 'list',
				doctype: 'Site Domain',
				filters: {
					site: this.site,
					dns_type: 'A',
					domain: ['!=', this.site]
				},
				limit: 1,
				auto: true
			};
		},
		changeRegionOptions() {
			return {
				url: 'press.api.site.change_region_options',
				params: {
					name: this.site
				},
				auto: true
			};
		},
		changeRegion() {
			return {
				url: 'press.api.site.change_region'
			};
		}
	},
	methods: {
		changeRegion() {
			toast.promise(
				this.$resources.changeRegion.submit({
					name: this.site,
					cluster: this.selectedRegion?.value,
					scheduled_datetime: this.datetimeInIST,
					skip_failing_patches: this.skipFailingPatches
				}),
				{
					success: () => {
						this.show = false;
						return `Site scheduled to be migrated to ${this.selectedRegion?.label}`;
					},
					loading: `Scheduling site to be migrated to ${this.selectedRegion?.label}...`,
					error: error =>
						error.messages?.length
							? error.messages.join('\n')
							: error.message || 'Failed to schedule site migration'
				}
			);
		},
		resetValues() {
			this.selectedRegion = null;
			this.targetDateTime = null;
		}
	}
};
</script>
