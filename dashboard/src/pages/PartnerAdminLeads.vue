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
		leadOwners() {
			return {
				url: 'press.api.partner.get_lead_owners',
				auto: true,
				initialData: [],
			};
		},
	},
	computed: {
		partnerAdminLeadsList() {
			let leadOwners = this.$resources.leadOwners.data || [];
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
								{ label: 'All', value: 'All' },
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
								{ label: 'All', value: 'All' },
								{ label: 'Open', value: 'Open' },
								{ label: 'Qualification', value: 'Qualification' },
								{ label: 'Demo/Making', value: 'Demo/Making' },
								{ label: 'Follow Up', value: 'Follow Up' },
								{ label: 'Proposal/Quotation', value: 'Proposal/Quotation' },
								{ label: 'Negotiation', value: 'Negotiation' },
								{ label: 'Ready to Close', value: 'Ready to Close' },
								{ label: 'In Process', value: 'In Process' },
								{ label: 'Won', value: 'Won' },
								{ label: 'Lost', value: 'Lost' },
								{ label: 'Junk', value: 'Junk' },
								{ label: 'Closed', value: 'Closed' },
							],
						},
						{
							type: 'select',
							fieldname: 'lead_owner',
							label: 'Lead Owner',
							options: [
								{ label: 'All', value: 'All' },
								...leadOwners.map((owner) => ({
									label: owner.label,
									value: owner.value,
								})),
							],
						},
						{
							type: 'checkbox',
							fieldname: 'is_starter_pack',
							label: 'Starter Pack',
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
