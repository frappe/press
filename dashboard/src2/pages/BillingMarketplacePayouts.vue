<template>
	<div class="p-5">
		<ObjectList :options="options" />
		<Dialog
			v-model="payoutDialog"
			:options="{ size: '4xl', title: showPayout?.name }"
		>
			<template #body-content>
				<template v-if="showPayout">
					<div
						v-if="showPayout.status === 'Empty'"
						class="text-base text-gray-600"
					>
						Nothing to show
					</div>
					<PayoutTable v-else :payoutId="showPayout.name" />
				</template>
			</template>
		</Dialog>
	</div>
</template>
<script>
import ObjectList from '../components/ObjectList.vue';
import { currency } from '../utils/format';
import PayoutTable from '../components/PayoutTable.vue';

export default {
	name: 'BillingMarketplacePayouts',
	props: ['tab'],
	data() {
		return {
			payoutDialog: false,
			showPayout: null
		};
	},
	components: {
		ObjectList,
		PayoutTable
	},
	computed: {
		options() {
			return {
				doctype: 'Payout Order',
				fields: [
					'period_end',
					'mode_of_payment',
					'status',
					'net_total_inr',
					'net_total_usd'
				],
				columns: [
					{
						label: 'Date',
						fieldname: 'period_end',
						format(value) {
							return Intl.DateTimeFormat('en-US', {
								year: 'numeric',
								month: 'short',
								day: 'numeric'
							}).format(new Date(value));
						}
					},
					{ label: 'Payment Mode', fieldname: 'mode_of_payment' },
					{ label: 'Status', fieldname: 'status', type: 'Badge' },
					{
						label: 'Net INR',
						fieldname: 'net_total_inr',
						format: value => currency(value, 'INR')
					},
					{
						label: 'Net USD',
						fieldname: 'net_total_usd',
						format: value => currency(value, 'USD')
					}
				],
				onRowClick: row => {
					this.showPayout = row;
					this.payoutDialog = true;
				}
			};
		}
	}
};
</script>
