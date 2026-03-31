<template>
	<div class="p-5">
		<ObjectList :options="partnerAuditsList" />
	</div>
</template>
<script setup>
import { computed, inject, h } from 'vue';
import ObjectList from '../ObjectList.vue';
import { icon, renderDialog } from '../../utils/components';
import router from '../../router';
import NewPartnerAudit from './NewPartnerAudit.vue';

const team = inject('team');

const partnerAuditsList = computed(() => {
	return {
		doctype: 'Partner Audit',
		fields: ['mode_of_audit', 'status', 'proposed_audit_date', 'audit_date'],
		filters: {
			team: team.doc.name,
		},
		columns: [
			{
				label: 'Audit Type',
				fieldname: 'mode_of_audit',
			},
			{
				label: 'Status',
				fieldname: 'status',
				type: 'Badge',
			},
			{
				label: 'Conducted By',
				fieldname: 'conducted_by',
			},
			{
				label: 'NC Count',
				fieldname: 'non_conformance_count',
				type: 'Badge',
				align: 'center',
			},
			{
				label: 'Requested Date',
				fieldname: 'proposed_audit_date',
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
			];
		},
		actions() {
			return [
				{
					label: 'Request for Audit',
					slots: {
						prefix: icon('plus'),
					},
					onClick: () => {
						return renderDialog(
							h(NewPartnerAudit, {
								modelValue: true,
							}),
						);
					},
				},
			];
		},
		onRowClick: (row) => {
			router.push({
				name: 'PartnerNCList',
				params: { partner_audit: row.name },
			});
		},
	};
});
</script>
