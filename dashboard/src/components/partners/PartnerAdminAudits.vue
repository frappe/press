<template>
	<div class="p-5">
		<ObjectList :options="partnerAuditsList" />
	</div>
</template>
<script>
import ObjectList from '../ObjectList.vue';

export default {
	name: 'PartnerAdminAudits',
	components: {
		ObjectList,
	},
	computed: {
		partnerAuditsList() {
			return {
				doctype: 'Partner Audit',
				fields: [
					'mode_of_audit',
					'status',
					'proposed_audit_date',
					'audit_date',
				],
				columns: [
					{
						label: 'Partner',
						fieldname: 'partner_team',
						width: 0.8,
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
						width: 0.5,
					},
					{
						label: 'Audit Type',
						fieldname: 'mode_of_audit',
						width: 0.5,
					},
					{
						label: 'Conducted By',
						fieldname: 'conducted_by',
						width: 0.8,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'NC Count',
						fieldname: 'non_conformance_count',
						width: 0.4,
						type: 'Badge',
						align: 'center',
					},
					{
						label: 'Requested Date',
						fieldname: 'proposed_audit_date',
						width: 0.8,
						format(value) {
							if (!value) return '';
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'long',
								day: 'numeric',
							}).format(new Date(value));
						},
					},
					{
						label: 'Audit Date',
						fieldname: 'audit_date',
						width: 0.8,
						format(value) {
							if (!value) return '';
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'long',
								day: 'numeric',
							}).format(new Date(value));
						},
					},
				],
				filterControls() {
					return [
						{
							type: 'date',
							fieldname: 'proposed_audit_date',
							label: 'Audit Date',
						},
						{
							type: 'select',
							fieldname: 'status',
							label: 'Status',
							options: [
								{ label: 'All', value: 'All' },
								{ label: 'Requested', value: 'Requested' },
								{ label: 'Scheduled', value: 'Scheduled' },
								{ label: 'In Progress', value: 'In Progress' },
								{ label: 'Completed', value: 'Completed' },
								{ label: 'On Hold', value: 'On Hold' },
								{ label: 'Cancelled', value: 'Cancelled' },
							],
						},
						{
							type: 'select',
							fieldname: 'mode_of_audit',
							label: 'Audit Type',
							options: [
								{ label: 'All', value: 'All' },
								{ label: 'In-Person', value: 'In-Person' },
								{ label: 'Online', value: 'Online' },
								{ label: 'Hybrid', value: 'Hybrid' },
							],
						},
					];
				},
				onRowClick: (row) => {
					this.$router.push({
						name: 'PartnerNCList',
						params: { partner_audit: row.name },
					});
				},
			};
		},
	},
};
</script>
