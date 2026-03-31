<template>
	<div>
		<ObjectList :options="options" />
	</div>
</template>
<script>
import { h } from 'vue';
import { toast } from 'vue-sonner';
import { FeatherIcon, Tooltip, Badge, Button } from 'frappe-ui';
import ObjectList from '../ObjectList.vue';
import Clock from '~icons/lucide/clock';
export default {
	name: 'PartnerApprovalRequests',
	components: {
		ObjectList,
	},
	computed: {
		options() {
			return {
				doctype: 'Partner Approval Request',
				fields: ['approved_by_partner', 'status'],
				columns: [
					{
						label: 'Customer Email',
						fieldname: 'customer_email',
						width: 0.8,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Customer Team',
						fieldname: 'requested_by',
						width: 0.8,
						class: 'truncate',
						format: (value) => {
							if (!value) return '';
							return value.length > 25 ? `${value.slice(0, 25)}...` : value;
						},
					},
					{
						label: 'Raised On',
						fieldname: 'creation',
						width: 0.6,
						format(value) {
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'long',
								day: 'numeric',
							}).format(new Date(value));
						},
					},
					{
						label: 'Frappe Approval',
						fieldname: 'approved_by_frappe',
						type: 'Component',
						align: 'center',
						width: 0.6,
						component({ row }) {
							if (row.approved_by_frappe) {
								return h(
									Tooltip,
									{
										text: 'Approved',
									},
									() =>
										h(FeatherIcon, {
											name: 'check-circle',
											class: 'h-4 w-4 text-green-600',
										}),
								);
							} else {
								return h(
									Tooltip,
									{
										text: 'Approval Pending',
									},
									() =>
										h(Clock, {
											class: 'h-4 w-4 text-yellow-500',
										}),
								);
							}
						},
					},
					{
						label: 'Partner Approval',
						fieldname: 'approved_by_partner',
						type: 'Component',
						align: 'center',
						width: 0.6,
						component({ row }) {
							if (row.approved_by_partner) {
								return h(
									Tooltip,
									{
										text: 'Approved',
									},
									() =>
										h(FeatherIcon, {
											name: 'check-circle',
											class: 'h-4 w-4 text-green-600',
										}),
								);
							} else {
								return h(
									Tooltip,
									{
										text: 'Approval Pending',
									},
									() =>
										h(Clock, {
											class: 'h-4 w-4 text-yellow-500',
										}),
								);
							}
						},
					},
					{
						label: '',
						type: 'Component',
						width: 0.8,
						align: 'center',
						component({ row, listResource }) {
							if (row.status === 'Pending' && row.approved_by_partner === 0) {
								return h(Button, {
									label: 'Approve',
									class: 'text-md',
									variant: 'subtle',
									onClick: () => {
										toast.promise(
											listResource.runDocMethod.submit({
												method: 'approve_partner_request',
												name: row.name,
											}),
											{
												loading: 'Approving...',
												success: 'Approval request sent to Frappe',
												error: 'Failed to Approve',
											},
										);
									},
								});
							} else if (
								row.status === 'Pending' &&
								row.approved_by_frappe === 0
							) {
								return h(Badge, {
									label: "Waiting for Frappe's approval",
									theme: 'blue',
									variant: 'subtle',
									size: 'md',
								});
							}
						},
					},
				],
				filters: {
					partner: this.$team.doc.name,
				},
				orderBy: 'creation desc',
			};
		},
	},
};
</script>
