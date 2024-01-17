<template>
	<div class="p-5">
		<ObjectList :options="options" />
		<Dialog
			v-model="contributionDialog"
			:options="{
				size: '3xl',
				title: 'Last Month + Current Month\'s Contribution '
			}"
		>
			<template #body-content>
				<template v-if="showInvoice">
					<div
						v-if="showInvoice.status === 'Empty'"
						class="text-base text-gray-600"
					>
						Nothing to show
					</div>
					<InvoiceTable v-else :invoiceId="showInvoice.name" />
				</template>
			</template>
		</Dialog>
	</div>
</template>
<script>
import ObjectList from '../ObjectList.vue';
import InvoiceTable from '../InvoiceTable.vue';
import { Dialog } from 'frappe-ui';
export default {
	name: 'PartnerCustomers',
	components: {
		ObjectList,
		InvoiceTable,
		Dialog
	},
	data() {
		return {
			contributionDialog: false,
			showInvoice: null
		};
	},
	computed: {
		options() {
			return {
				doctype: 'Team',
				fields: ['user', 'billing_name', 'payment_mode', 'currency'],
				columns: [
					{
						label: 'Name',
						fieldname: 'billing_name'
					},
					{
						label: 'Email',
						fieldname: 'user'
					},
					{
						label: 'Payment Mode',
						fieldname: 'payment_mode'
					},
					{
						label: 'Currency',
						fieldname: 'currency'
					}
				],
				filters: {
					enabled: 1,
					partner_email: this.$team.doc.partner_email,
					erpnext_partner: 0
				},
				onRowClick: row => {
					this.contributionDialog = row;
					this.showInvoice = row;
				}
			};
		}
	}
};
</script>
