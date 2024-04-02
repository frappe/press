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
					<PartnerCustomerInvoices :customerTeam="showInvoice.name" />
				</template>
			</template>
		</Dialog>
		<Dialog
			v-model="transferCreditsDialog"
			:modelValue="true"
			:options="{ title: 'Transfer Credits' }"
		>
			<template #body-content>
				<p class="text-p-base pb-3">
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
							partner: $team.doc.name
						})
					"
				>
					Transfer
				</Button>
			</template>
		</Dialog>
		<Dialog
			v-model="showConfirmationDialog"
			:modelValue="false"
			:options="{ title: 'Credits Transferred Successfully' }"
		>
			<template #body-content>
				<p class="text-p-base">
					{{ formatCurrency(amount) }} credits have been transferred to
					<strong>{{ customerTeam.billing_name }}</strong>
				</p>
				<span class="text-base text-gray-700 font-medium"
					>Credits available: {{ creditBalance() }}</span
				>
			</template>
		</Dialog>
	</div>
</template>
<script>
import ObjectList from '../ObjectList.vue';
import PartnerCustomerInvoices from './PartnerCustomerInvoices.vue';
import { Dialog, ErrorMessage } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { userCurrency } from '../../utils/format';
export default {
	name: 'PartnerCustomers',
	components: {
		ObjectList,
		PartnerCustomerInvoices,
		Dialog,
		ErrorMessage
	},
	data() {
		return {
			contributionDialog: false,
			showInvoice: null,
			transferCreditsDialog: false,
			customerTeam: null,
			amount: 0.0,
			showConfirmationDialog: false
		};
	},
	resources: {
		transferCredits() {
			return {
				url: 'press.api.account.transfer_credits',
				onSuccess() {
					this.transferCreditsDialog = false;
					this.showConfirmationDialog = true;
					toast.success('Credits Transferred');
				}
			};
		},
		getBalance: {
			url: 'press.api.billing.get_balance_credit',
			auto: true
		}
	},
	computed: {
		options() {
			return {
				doctype: 'Team',
				fields: ['user', 'billing_name', 'payment_mode', 'currency', 'name'],
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
				rowActions: ({ row, listResource }) => {
					return [
						{
							label: 'Transfer Credits',
							onClick: () => {
								this.transferCreditsDialog = true;
								this.customerTeam = row;
							}
						},
						{
							label: 'View Contributions',
							onClick: () => {
								this.showInvoice = row;
								this.contributionDialog = true;
							}
						}
					];
				},
				filters: {
					enabled: 1,
					partner_email: this.$team.doc.partner_email,
					erpnext_partner: 0
				}
			};
		}
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
				parseFloat(this.$resources.getBalance.data) - parseFloat(this.amount)
			);
		}
	}
};
</script>
