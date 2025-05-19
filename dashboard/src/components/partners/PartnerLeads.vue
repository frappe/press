<template>
	<div class="p-4">
		<ObjectList :options="partnerLeadsList" />
	</div>
</template>
<script>
import ObjectList from '../ObjectList.vue';
export default {
	name: 'PartnerLeads',
	components: {
		ObjectList,
	},
	computed: {
		partnerLeadsList() {
			return {
				resource() {
					return {
						url: 'press.api.partner.get_partner_leads',
						auto: true,
						initialData: [],
						transform(data) {
							return data.map((d) => {
								return {
									name: d.name,
									lead_name: d.lead_name || '',
									organization: d.organization_name || '',
									lead_source: d.lead_source || '',
									status: d.status || '',
								};
							});
						},
					};
				},
				columns: [
					{
						label: 'Lead ID',
						fieldname: 'name',
					},
					{
						label: 'Lead Name',
						fieldname: 'lead_name',
					},
					{
						label: 'Organization',
						fieldname: 'organization',
					},
					{
						label: 'Lead Source',
						fieldname: 'lead_source',
					},
					{
						label: 'Status',
						fieldname: 'status',
					},
				],
				onRowClick: (row) => {
					console.log('Row clicked:', row);
					this.$router.push({
						name: 'PartnerLeadDetails',
						params: { leadId: row.name },
					});
				},
			};
		},
	},
};
</script>
