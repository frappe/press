<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Restore Backup on Another Site',
			actions: [
				{
					label: 'Restore',
					variant: 'solid',
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
		</template>
	</Dialog>
</template>

<script>
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
	resources: {
		sites() {
			return {
				type: 'list',
				doctype: 'Site',
				fields: ['host_name', 'name'],
				filters: { name: ['!=', this.site] },
				auto: true
			};
		}
	}
};
</script>
