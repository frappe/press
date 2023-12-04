<template>
	<Card title="Payment methods" :subtitle="subtitle">
		<template #actions>
			<Button @click="showAddCardDialog = true"> Add Card </Button>
			<Dialog :options="{ title: 'Add new card' }" v-model="showAddCardDialog">
				<template v-slot:body-content>
					<StripeCard
						class="mb-1"
						v-if="showAddCardDialog"
						@complete="
							showAddCardDialog = false;
							$resources.paymentMethods.reload();
						"
					/>
				</template>
			</Dialog>
		</template>
		<div class="space-y-3">
			<div
				class="flex items-center justify-between rounded-lg border p-5"
				v-for="card in $resources.paymentMethods.data"
				:key="card.name"
			>
				<div class="flex">
					<component
						class="mr-6 w-12 h-12"
						:is="cardBrand[card.brand]"
						v-if="card.brand"
					/>
					<component class="mr-6 w-12 h-12" :is="cardBrand['generic']" v-else />
					<div class="my-auto">
						<div class="text-lg font-medium text-gray-900">
							{{ card.name_on_card }} <span class="text-gray-500">••••</span>
							{{ card.last_4 }}
							<Badge v-if="card.is_default" label="Default" />
						</div>
						<div class="mt-1 text-sm text-gray-600">
							<span>
								Valid till {{ card.expiry_month }}/{{ card.expiry_year }}
							</span>
							·
							<span>Added on {{ $date(card.creation).toLocaleString() }}</span>
						</div>
					</div>
				</div>
				<Dropdown :options="dropdownItems(card)" right>
					<template v-slot="{ open }">
						<Button icon="more-horizontal" />
					</template>
				</Dropdown>
			</div>
		</div>
	</Card>
	<FinalizeInvoicesDialog v-model="showFinalizeDialog" />
	<Dialog
		:options="{
			title: 'Remove Payment Method',
			actions: [
				{
					label: 'Remove',
					variant: 'solid',
					theme: 'red',
					onClick: () => {
						$resources.remove.submit({ name: cardToRemove.name }).then(() => {
							$resources.paymentMethods.reload();
							this.showRemoveCardDialog = false;
						});
					}
				},
				{
					label: 'Cancel',
					onClick: () => (this.showRemoveCardDialog = false)
				}
			]
		}"
		v-model="showRemoveCardDialog"
	>
		<template v-slot:body-content>
			<span>Are you sure you want to remove this payment method?</span>
			<br /><br />
			<span v-if="$resources.paymentMethods.data.length === 1">
				If you intend to close your account please check the docs for
				<Link
					target="_blank"
					href="https://frappecloud.com/docs/billing/disable-account"
					>cancelling subscription.</Link
				>
				Frappe Cloud is not responsible for any refund if the account is not
				closed properly.
			</span>
		</template>
	</Dialog>
</template>

<script>
import { defineAsyncComponent } from 'vue';
import Link from '@/components/Link.vue';
import FinalizeInvoicesDialog from './FinalizeInvoicesDialog.vue';

export default {
	name: 'AccountBillingCards',
	data() {
		return {
			showAddCardDialog: false,
			showRemoveCardDialog: false,
			showFinalizeDialog: false,
			cardToRemove: null
		};
	},
	resources: {
		paymentMethods: {
			url: 'press.api.billing.get_payment_methods',
			auto: true
		},
		setAsDefault: {
			url: 'press.api.billing.set_as_default'
		},
		remove() {
			return {
				url: 'press.api.billing.remove_payment_method',
				onSuccess: data => {
					if (data === 'Unpaid Invoices') {
						this.showFinalizeDialog = true;
					}
				}
			};
		}
	},
	components: {
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		),
		FinalizeInvoicesDialog
	},
	computed: {
		subtitle() {
			if (
				this.$resources.paymentMethods.loading ||
				this.$resources.paymentMethods.data?.length > 0
			) {
				return 'Cards you have added for automatic billing';
			}
			return "You haven't added any cards yet";
		},
		cardBrand() {
			return {
				'master-card': defineAsyncComponent(() =>
					import('@/components/icons/cards/MasterCard.vue')
				),
				visa: defineAsyncComponent(() =>
					import('@/components/icons/cards/Visa.vue')
				),
				amex: defineAsyncComponent(() =>
					import('@/components/icons/cards/Amex.vue')
				),
				jcb: defineAsyncComponent(() =>
					import('@/components/icons/cards/JCB.vue')
				),
				generic: defineAsyncComponent(() =>
					import('@/components/icons/cards/Generic.vue')
				),
				'union-pay': defineAsyncComponent(() =>
					import('@/components/icons/cards/UnionPay.vue')
				)
			};
		}
	},
	methods: {
		dropdownItems(card) {
			return [
				!card.is_default && {
					label: 'Set as default',
					onClick: () => this.confirmSetAsDefault(card)
				},
				{
					label: 'Remove',
					onClick: () => {
						this.cardToRemove = card;
						this.showRemoveCardDialog = true;
					}
				}
			];
		},
		confirmSetAsDefault(card) {
			this.$confirm({
				title: 'Set as default',
				message: 'Set this card as the default payment method?',
				actionLabel: 'Set as default',
				resource: this.$resources.setAsDefault,
				action: closeDialog => {
					this.$resources.setAsDefault.submit({ name: card.name }).then(() => {
						this.$resources.paymentMethods.reload();
						closeDialog();
					});
				}
			});
		}
	}
};
</script>
