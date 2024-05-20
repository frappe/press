<template>
	<div class="px-4">
		<div class="mt-3 min-h-0 flex-1 overflow-y-auto">
			<ListView
				:columns="columns"
				:rows="partnerCustomers"
				:options="{
					selectable: false,
					onRowClick: row => {
						showInvoice = row;
						contributionDialog = true;
					},
					getRowRoute: null
				}"
				row-key="email"
			>
				<ListHeader>
					<ListHeaderItem
						v-for="column in columns"
						:key="column.key"
						:item="column"
					/>
				</ListHeader>
				<ListRows>
					<div
						v-if="partnerCustomers.length === 0"
						class="text-center text-sm leading-10 text-gray-500"
					>
						No results found
					</div>
					<ListRow v-for="(row, i) in rows" :row="row" :key="row.email">
						<template v-slot="{ column, item }">
							<ObjectListCell :row="row" :column="column" :idx="i" />
						</template>
					</ListRow>
				</ListRows>
			</ListView>
		</div>
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
import ObjectListCell from '../ObjectListCell.vue';
import PartnerCustomerInvoices from './PartnerCustomerInvoices.vue';
import {
	Dialog,
	ErrorMessage,
	ListHeader,
	ListRow,
	ListView,
	ListHeaderItem,
	ListRows
} from 'frappe-ui';
import { toast } from 'vue-sonner';
import { userCurrency } from '../../utils/format';
export default {
	name: 'PartnerCustomers',
	components: {
		ObjectList,
		PartnerCustomerInvoices,
		Dialog,
		ErrorMessage,
		ListView,
		ListHeader,
		ListRow,
		ListHeaderItem,
		ListRows,
		ObjectListCell
	},
	data() {
		return {
			contributionDialog: false,
			showInvoice: null,
			transferCreditsDialog: false,
			customerTeam: null,
			amount: 0.0,
			showConfirmationDialog: false,
			partnerCustomers: []
		};
	},
	resources: {
		getPartnerCustomers() {
			return {
				url: 'press.api.account.get_partner_customers',
				onSuccess(data) {
					this.partnerCustomers = data.map(d => {
						return {
							email: d.user,
							billing_name: d.billing_name || '',
							payment_mode: d.payment_mode || '',
							currency: d.currency,
							name: d.name
						};
					});
				},
				auto: true
			};
		},
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
		columns() {
			return [
				{
					label: 'Name',
					key: 'billing_name'
				},
				{
					label: 'Email',
					key: 'email'
				},
				{
					label: 'Payment Mode',
					key: 'payment_mode'
				},
				{
					label: 'Currency',
					key: 'currency'
				}
			];
		},
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
