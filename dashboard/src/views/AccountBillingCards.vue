<template>
	<Card title="Payment methods" :subtitle="subtitle">
		<template #actions>
			<Button @click="showAddCardDialog = true"> Add Card </Button>
			<Dialog title="Add new card" v-model="showAddCardDialog">
				<StripeCard
					class="mb-1"
					v-if="showAddCardDialog"
					@complete="
						showAddCardDialog = false;
						$resources.paymentMethods.reload();
					"
				/>
			</Dialog>
		</template>
		<div class="max-h-52 space-y-3">
			<div
				class="flex items-center justify-between rounded-lg border p-5"
				v-for="card in $resources.paymentMethods.data"
				:key="card.name"
			>
				<div>
					<div class="text-lg font-medium text-gray-900">
						{{ card.name_on_card }} <span class="text-gray-500">••••</span>
						{{ card.last_4 }}
						<Badge v-if="card.is_default">Default</Badge>
					</div>
					<div class="mt-1 text-sm text-gray-600">
						<span>
							Valid till {{ card.expiry_month }}/{{ card.expiry_year }}
						</span>
						·
						<span>Added on {{ $date(card.creation).toLocaleString() }}</span>
					</div>
				</div>
				<Dropdown :items="dropdownItems(card)" right>
					<template v-slot="{ toggleDropdown }">
						<Button icon="more-horizontal" @click="toggleDropdown()" />
					</template>
				</Dropdown>
			</div>
		</div>
	</Card>
</template>
<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'AccountBillingCards',
	resources: {
		paymentMethods: 'press.api.billing.get_payment_methods',
		setAsDefault: {
			method: 'press.api.billing.set_as_default'
		},
		remove: {
			method: 'press.api.billing.remove_payment_method'
		}
	},
	components: {
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		)
	},
	data() {
		return {
			showAddCardDialog: false
		};
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
		}
	},
	methods: {
		dropdownItems(card) {
			return [
				!card.is_default && {
					label: 'Set as default',
					action: () => this.confirmSetAsDefault(card)
				},
				{
					label: 'Remove',
					action: () => this.confirmRemove(card)
				}
			];
		},
		confirmSetAsDefault(card) {
			this.$confirm({
				title: 'Set as default',
				message: 'Set this card as the default payment method?',
				actionLabel: 'Set as default',
				resource: this.$resources.setAsDefault,
				action: () => {
					this.$resources.setAsDefault
						.submit({ name: card.name })
						.then(() => this.$resources.paymentMethods.reload());
				}
			});
		},
		confirmRemove(card) {
			this.$confirm({
				title: 'Remove payment method',
				message: 'Are you sure you want to remove this payment method?',
				actionLabel: 'Remove',
				actionType: 'danger',
				resource: this.$resources.remove,
				action: () => {
					this.$resources.remove
						.submit({ name: card.name })
						.then(() => this.$resources.paymentMethods.reload());
				}
			});
		}
	}
};
</script>
