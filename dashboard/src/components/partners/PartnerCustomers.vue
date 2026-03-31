<template>
	<div class="p-4">
		<ObjectList :options="partnerCustomerList" />
		<Dialog
			v-model="contributionDialog"
			:options="{
				size: '3xl',
				title: 'Last 6 Month\'s Contribution',
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
					<PartnerCustomerInvoices
						:customerTeam="showInvoice.name"
						:customerCurrency="showInvoice.currency"
					/>
				</template>
			</template>
		</Dialog>
		<Dialog
			v-model="transferCreditsDialog"
			:options="{ title: 'Transfer Credits' }"
		>
			<template #body-content>
				<p class="pb-3 text-p-base">
					Enter the equivalent amount of credits (in {{ $team.doc.currency }})
					you wish to transfer.
				</p>
				<FormControl placeholder="Amount" v-model="amount" autocomplete="off" />
				<ErrorMessage
					class="mt-2"
					:message="$resources.transferCredits.error"
				/>
			</template>
			<template #actions>
				<Button
					type="primary"
					variant="solid"
					class="w-full"
					:loading="$resources.transferCredits.loading"
					@click="
						$resources.transferCredits.submit({
							amount: amount,
							customer: customerTeam.name,
						})
					"
				>
					Transfer
				</Button>
			</template>
		</Dialog>
		<Dialog
			v-model="showConfirmationDialog"
			:options="{ title: 'Credits Transferred Successfully' }"
		>
			<template #body-content>
				<p class="text-p-base">
					{{ formatCurrency(amount) }} credits have been transferred to
					<strong>{{ customerTeam.billing_name }}</strong>
				</p>
				<span class="text-base font-medium text-gray-700"
					>Credits available: {{ creditBalance() }}</span
				>
			</template>
		</Dialog>
		<Dialog
			v-model="showApprovalRequestsDialog"
			:options="{
				title: 'Customer Approval Requests',
				size: '6xl',
			}"
		>
			<template #body-content>
				<PartnerApprovalRequests />
			</template>
		</Dialog>
	</div>
</template>
<script>
import PartnerCustomerInvoices from './PartnerCustomerInvoices.vue';
import ObjectList from '../ObjectList.vue';
import { Dialog, ErrorMessage } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { userCurrency } from '../../utils/format';
import PartnerApprovalRequests from './PartnerApprovalRequests.vue';

export default {
	name: 'PartnerCustomers',
	components: {
		PartnerCustomerInvoices,
		Dialog,
		ErrorMessage,
		ObjectList,
		PartnerApprovalRequests,
	},
	data() {
		return {
			contributionDialog: false,
			showInvoice: null,
			transferCreditsDialog: false,
			customerTeam: null,
			amount: 0.0,
			showConfirmationDialog: false,
			showApprovalRequestsDialog: false,
		};
	},
	resources: {
		transferCredits() {
			return {
				url: 'press.api.partner.transfer_credits',
				onSuccess(data) {
					this.amount = data;
					this.transferCreditsDialog = false;
					this.showConfirmationDialog = true;
					toast.success('Credits Transferred');
				},
			};
		},
		getBalance: {
			url: 'press.api.billing.get_balance_credit',
			auto: true,
		},
	},
	computed: {
		partnerCustomerList() {
			return {
				resource() {
					return {
						url: 'press.api.partner.get_partner_customers',
						transform(data) {
							return data.map((d) => {
								return {
									email: d.user,
									billing_name: d.billing_name || '',
									payment_mode: d.payment_mode || '',
									currency: d.currency,
									name: d.name,
								};
							});
						},
						initialData: [],
						auto: true,
					};
				},
				columns: [
					{
						label: 'Name',
						fieldname: 'billing_name',
					},
					{
						label: 'Email',
						fieldname: 'email',
					},
					{
						label: 'Payment Mode',
						fieldname: 'payment_mode',
					},
					{
						label: 'Currency',
						fieldname: 'currency',
						width: 0.5,
					},
					{
						label: 'Contributions',
						type: 'Button',
						width: 0.5,
						align: 'center',
						Button: ({ row }) => {
							return {
								label: 'View',
								onClick: () => {
									this.showInvoice = row;
									this.contributionDialog = true;
								},
							};
						},
					},
					{
						label: '',
						type: 'Button',
						width: 0.8,
						align: 'right',
						key: 'actions',
						Button: ({ row }) => {
							return {
								label: 'Transfer Credits',
								onClick: () => {
									this.transferCreditsDialog = true;
									this.customerTeam = row;
								},
							};
						},
					},
				],
				actions: () => {
					return [
						{
							label: 'Customer Approval Requests',
							onClick: () => {
								this.showApprovalRequestsDialog = true;
							},
						},
					];
				},
			};
		},
	},
	methods: {
		formatCurrency(value) {
			if (value === 0) {
				return '';
			}
			return userCurrency(value);
		},
		creditBalance() {
			return this.formatCurrency(
				parseFloat(this.$resources.getBalance.data) - parseFloat(this.amount),
			);
		},
	},
};
</script>
