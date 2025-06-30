<template>
	<div class="p-4">
		<div v-if="partnerLeadsList">
			<ObjectList :options="partnerLeadsList" />
		</div>
		<div v-else class="text-base text-gray-600">
			No partner leads available.
		</div>
	</div>
</template>
<script>
import ObjectList from '../ObjectList.vue';
import { icon, renderDialog } from '../../utils/components';
import NewPartnerLead from './NewPartnerLead.vue';
import { h } from 'vue';
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
									partner_team: d.partner_team || '',
								};
							});
						},
					};
				},
				columns: [
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
						type: 'Badge',
					},
					{
						label: 'Lead ID',
						fieldname: 'name',
					},
					{
						label: 'Partner',
						fieldname: 'partner_team',
						condition: () => Boolean(this.$team.doc.is_desk_user),
					},
				],
				filterControls() {
					return [
						{
							type: 'select',
							fieldname: 'status',
							label: 'Status',
							options: [
								'',
								'Open',
								'In Process',
								'Won',
								'Lost',
								'Junk',
								'Passed to Other Partner',
								'Other',
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
					];
				},
				onRowClick: (row) => {
					this.$router.push({
						name: 'LeadOverview',
						params: { leadId: row.name },
					});
				},
				primaryAction: () => {
					return {
						label: 'Add Lead',
						variant: 'solid',
						slots: {
							prefix: icon('plus'),
						},
						onClick: () => {
							return renderDialog(
								h(NewPartnerLead, {
									modelValue: true,
								}),
							);
						},
					};
				},
			};
		},
		statusTheme() {
			return {
				Open: 'blue',
				'In Process': 'orange',
				Won: 'green',
				Lost: 'red',
				Junk: 'gray',
				'Passed to Other Partner': 'gray',
			};
		},
	},
};
</script>
