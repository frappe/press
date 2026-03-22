<template>
	<div class="p-5">
		<!-- <div class="-m-5 flex divide-x">
			<div class="w-1/3">dd</div>
			<div class="w-2/3 overflow-auto">
				data3
			</div>
		</div> -->
		<ObjectList :options="partnerAuditsList" />
	</div>
</template>
<script setup>
import { computed, inject } from 'vue';
import ObjectList from '../ObjectList.vue';
import { icon } from '../../utils/components';
import router from '../../router';

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
				label: 'Conducted By',
				fieldname: 'conducted_by',
			},
			{
				label: 'Status',
				fieldname: 'status',
				type: 'Badge',
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
		actions() {
			return [
				{
					label: 'Request for Audit',
					slots: {
						prefix: icon('plus'),
					},
					onClick: () => {
						console.log('Request for Audit');
						// router.push({ name: 'PartnerNCList' });
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
