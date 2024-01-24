<template>
	<Alert title="Account Setup" v-if="!$account.hasBillingInfo">
		{{ message }}
		<template #actions>
			<Button
				variant="solid"
				@click="
					isDefaultPaymentModeCard
						? (showPrepaidCreditsDialog = true)
						: (showCardDialog = true)
				"
				class="whitespace-nowrap"
			>
				{{
					isDefaultPaymentModeCard ? 'Add Balance' : 'Add Billing Information'
				}}
			</Button>
		</template>
		<BillingInformationDialog v-model="showCardDialog" v-if="showCardDialog" />
		<PrepaidCreditsDialog
			v-if="showPrepaidCreditsDialog"
			v-model:show="showPrepaidCreditsDialog"
			:minimum-amount="$account.team.currency === 'INR' ? 10 : 1"
			@success="handleAddPrepaidCreditsSuccess"
		/>
	</Alert>
</template>
<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'AlertBillingInformation',
	components: {
		BillingInformationDialog: defineAsyncComponent(() =>
			import('./BillingInformationDialog.vue')
		),
		PrepaidCreditsDialog: defineAsyncComponent(() =>
			import('./PrepaidCreditsDialog.vue')
		)
	},
	data() {
		return {
			showCardDialog: false,
			showPrepaidCreditsDialog: false
		};
	},
	methods: {
		handleAddPrepaidCreditsSuccess() {
			this.showPrepaidCreditsDialog = false;
		}
	},
	computed: {
		isDefaultPaymentModeCard() {
			return this.$account.team.payment_mode == 'Card';
		},
		message() {
			if (this.isDefaultPaymentModeCard) {
				return "We couldn't verify your card with micro charge. Please add some balance to your account to start creating sites.";
			} else {
				return "You haven't added your billing information yet. Add it to start creating sites.";
			}
		}
	}
};
</script>
