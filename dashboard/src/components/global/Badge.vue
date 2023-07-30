<template>
	<Badge :label="label" :theme="color" />
</template>

<script>
import { Badge } from 'frappe-ui';

export default {
	name: Badge,
	props: ['label'],
	components: {
		Badge
	},
	computed: {
		color() {
			return {
				Approved: 'green',
				Broken: 'red',
				Installing: 'orange',
				'Update Available': 'blue',
				Enabled: 'blue',
				'Awaiting Approval': 'orange',
				'Awaiting Deploy': 'orange',
				Deployed: 'green',
				Expired: 'red',
				Paid: 'green',
				Unpaid: 'orange',
				'Invoice Created': 'blue',
				Rejected: 'red',
				'In Review': 'orange',
				'Attention Required': 'red',
				Active: 'green',
				Trial: 'orange',
				Published: 'green',
				Owner: 'blue',
				Primary: 'green'
			}[this.label];
		}
	}
};
</script>
