<template>
	<div class="p-4">
		<div class="grid grid-cols-4 gap-5 pb-4">
			<NumberChart
				:config="{
					title: 'Total Leads',
					value: $resources.leadStats.data?.total || 0,
				}"
				class="border rounded-md"
			/>

			<NumberChart
				:config="{
					title: 'Open',
					value: $resources.leadStats.data?.open || 0,
				}"
				class="border rounded-md"
			/>

			<NumberChart
				:config="{
					title: 'Won',
					value: $resources.leadStats.data?.won || 0,
				}"
				class="border rounded-md"
			/>

			<NumberChart
				:config="{
					title: 'Lost',
					value: $resources.leadStats.data?.lost || 0,
				}"
				class="border rounded-md"
			/>
		</div>

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
import { NumberChart } from 'frappe-ui';
import { h } from 'vue';
export default {
	name: 'PartnerLeads',
	components: {
		ObjectList,
		NumberChart,
	},
	resources: {
		leadStats() {
			return {
				url: 'press.api.partner.get_lead_stats',
				auto: true,
			};
		},
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
						width: 0.6,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Organization',
						fieldname: 'organization',
						width: 0.6,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Lead Source',
						fieldname: 'lead_source',
						width: 0.5,
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
						width: 0.5,
					},
					{
						label: 'Partner',
						fieldname: 'partner_team',
						width: 0.6,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
						condition: () => Boolean(this.$team.doc.is_desk_user),
					},
				],
				filterControls() {
					return [
						{
							type: 'data',
							fieldname: 'lead_name',
							label: 'Lead Name',
						},
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
						{
							type: 'select',
							fieldname: 'source',
							label: 'Lead Source',
							options: [
								{ label: 'Partner Owned', value: 'Partner Owned' },
								{ label: 'Passed to Partner', value: 'Passed to Partner' },
								{ label: 'Partner Listing', value: 'Partner Listing' },
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
				orderBy: 'modified desc',
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
