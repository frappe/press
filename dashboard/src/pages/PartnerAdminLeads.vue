<template>
	<div class="p-5">
		<ObjectList :options="partnerAdminLeadsList" />
	</div>
</template>
<script>
import ObjectList from '../components/ObjectList.vue';
export default {
	name: 'PartnerAdminLeads',
	components: {
		ObjectList,
	},
	resources: {
		originList() {
			return {
				type: 'list',
				doctype: 'Partner Lead Origin',
				fields: ['name'],
				auto: true,
			};
		},
	},
	computed: {
		partnerAdminLeadsList() {
			return {
				doctype: 'Partner Lead',
				fields: [],
				columns: [
					{
						label: 'Lead Name',
						fieldname: 'lead_name',
					},
					{
						label: 'Organization',
						fieldname: 'organization_name',
					},
					{
						label: 'Source',
						fieldname: 'lead_source',
					},
					{
						label: 'Partner',
						fieldname: 'company_name',
						width: 0.6,
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
					},
					{
						label: 'Lead ID',
						fieldname: 'name',
						width: 0.4,
					},
				],
				filterControls() {
					return [
						{
							type: 'data',
							fieldname: 'search-text',
							label: 'Search',
						},
						{
							type: 'select',
							fieldname: 'source',
							label: 'Source',
							options: [
								{ label: 'Partner Owned', value: 'Partner Owned' },
								{ label: 'Passed to Partner', value: 'Passed to Partner' },
								{ label: 'Partner Listing', value: 'Partner Listing' },
							],
						},
						{
							type: 'select',
							fieldname: 'status',
							label: 'Status',
							options: [
								{ label: 'Open', value: 'Open' },
								{ label: 'In Process', value: 'In Process' },
								{ label: 'Won', value: 'Won' },
								{ label: 'Lost', value: 'Lost' },
								{ label: 'Junk', value: 'Junk' },
								{
									label: 'Pass to Other Partner',
									value: 'Pass to Other Partner',
								},
							],
						},
						{
							type: 'select',
							fieldname: 'origin',
							label: 'Origin',
							options: this.leadOrigins,
						},
					];
				},
				orderBy: 'modified desc',
				onRowClick(row) {
					this.$router.push({
						name: 'PartnerLeadDetail',
						params: { leadId: row.name },
					});
				},
			};
		},
		leadOrigins() {
			return this.$resources.originList.data.map((d) => {
				return { label: d.name, value: d.name };
			});
		},
	},
};
</script>
