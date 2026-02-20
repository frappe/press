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
			const resources = this.$resources.originList.data || [];
			const origins = resources.map((d) => {
				return { label: d.name, value: d.name };
			});

			return {
				doctype: 'Partner Lead',
				columns: [
					{
						label: 'Lead Name',
						fieldname: 'lead_name',
						width: 0.6,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Organization',
						fieldname: 'organization_name',
						width: 0.6,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Source',
						fieldname: 'lead_source',
						width: 0.5,
					},
					{
						label: 'Partner',
						fieldname: 'company_name',
						width: 0.6,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
						width: 0.4,
						align: 'center',
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
							label: 'Search for org, lead or partner',
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
							fieldname: 'engagement_stage',
							label: 'Engagement Stage',
							options: [
								'',
								'Demo',
								'Qualification',
								'Quotation',
								'Ready for Closing',
								'Negotiation',
								'Learning',
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
							options: origins,
						},
					];
				},
				onRowClick: (row) => {
					this.$router.push({
						name: 'LeadOverview',
						params: { leadId: row.name },
					});
				},
			};
		},
	},
};
</script>
