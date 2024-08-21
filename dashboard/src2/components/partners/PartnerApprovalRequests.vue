<template>
	<div class="p-5">
		<ObjectList :options="options" />
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import ObjectList from '../ObjectList.vue';
export default {
	name: 'PartnerApprovalRequests',
	components: {
		ObjectList
	},
	computed: {
		options() {
			return {
				doctype: 'Partner Approval Request',
				columns: [
					{
						label: 'Customer Email',
						fieldname: 'customer_email'
					},
					{
						label: 'Customer Team ID',
						fieldname: 'requested_by'
					},
					{
						label: 'Raised On',
						fieldname: 'creation',
						format(value) {
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'long',
								day: 'numeric'
							}).format(new Date(value));
						}
					},
					{
						label: 'Approval By Frappe',
						fieldname: 'approved_by_frappe',
						type: 'Badge',
						format(value) {
							return value ? 'Approved' : 'Pending';
						}
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge'
					},
					{
						label: '',
						type: 'Button',
						Button: ({ row, listResource }) => {
							if (row.status === 'Pending' && row.approved_by_partner === 0) {
								return {
									label: 'Approve',
									type: 'primary',
									onClick: () => {
										toast.promise(
											listResource.runDocMethod.submit({
												method: 'approve_partner_request',
												name: row.name
											}),
											{
												loading: 'Approving...',
												success: 'Approved',
												error: 'Failed to Approve'
											}
										);
									}
								};
							}
						}
					}
				],
				filters: {
					partner: this.$team.doc.name
				},
				orderBy: 'creation desc'
			};
		}
	}
};
</script>
