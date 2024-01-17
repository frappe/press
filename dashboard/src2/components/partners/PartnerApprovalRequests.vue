<template>
	<div class="p-5">
		<ObjectList :options="options" />
	</div>
</template>
<script>
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
				fields: ['requested_by', 'partner_email', 'status'],
				columns: [
					{
						label: 'Customer Email',
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
						label: 'Status',
						fieldname: 'status',
						type: 'Badge'
					}
				],
				filters: {
					partner_email: this.$team.doc.partner_email
				},
				orderBy: 'creation desc'
			};
		}
	}
};
</script>
