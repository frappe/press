<template>
	<Card title="Partner Request Status" v-if="!$account.team.erpnext_partner">
		<template #actions>
			<Badge
				:variant="'solid'"
				:theme="this.partnerRequestStatus === 'Pending' ? 'red' : 'green'"
				size="lg"
				:label="this.partnerRequestStatus"
			/>
		</template>
	</Card>
</template>
<script>
export default {
	name: 'PartnerRequestStatus',
	data() {
		return {
			partnerRequestStatus: null
		};
	},
	resources: {
		getStatus: {
			url: 'press.api.account.get_partner_request_status',
			params: {
				team: $account.team.name
			},
			onSuccess(data) {
				console.log(data);
				this.partnerRequestStatus = data;
			},
			auto: true
		}
	}
};
</script>
