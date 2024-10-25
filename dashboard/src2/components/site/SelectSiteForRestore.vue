<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Restore Backup on Another Site',
			actions: [
				{
					label: 'Restore',
					variant: 'solid',
					theme: 'red',
					disabled: !selectedSite,
					onClick: () => {
						this.$emit('restore', this.selectedSite.value);
						showDialog = false;
					}
				}
			]
		}"
	>
		<template #body-content>
			<FormControl
				label="Select the site where you want to restore the backup"
				class="mt-4"
				type="autocomplete"
				v-model="selectedSite"
				:options="
					($resources.sites.data || []).map(site => {
						return {
							label: site.host_name || site.name,
							value: site.name
						};
					})
				"
			/>
			<AlertBanner
				v-if="selectedSite"
				class="mt-4"
				type="warning"
				:title="`Restoring will overwrite the current data of <strong>${selectedSite.value}</strong> with the backup data of <strong>${site}</strong>`"
			/>
		</template>
	</Dialog>
</template>

<script>
import AlertBanner from '../AlertBanner.vue';

export default {
	name: 'SelectSiteForRestore',
	props: ['site'],
	emits: ['restore'],
	data() {
		return {
			selectedSite: null,
			showDialog: true
		};
	},
	components: {
		AlertBanner
	},
	resources: {
		sites() {
			return {
				type: 'list',
				doctype: 'Site',
				fields: ['host_name', 'name'],
				filters: { name: ['!=', this.site] },
				pageLength: 500,
				auto: true
			};
		}
	}
};
</script>
