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
				filterControls() {
					return [
						{
							type: 'select',
							label: 'Status',
							class: 'w-36',
							fieldname: 'status',
							options: ['', 'Draft', 'Paid', 'Commissioned']
						}
					];
				},
				orderBy: 'creation desc',
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
						label: 'Total',
						fieldname: 'net_total_inr',
						format: (_, row) => {
							let total = 0;
							if (this.$team.doc.currency === 'INR') {
								total = row.net_total_inr + row.net_total_usd * 82;
							} else {
								total = row.net_total_inr / 82 + row.net_total_usd;
							}

							return this.$format.userCurrency(total);
						}
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
