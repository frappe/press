<template>
	<div class="px-60 py-6">
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
			<!-- Adding Mpesa Details -->
			<div
				v-if="$team.doc.country === 'Kenya'"
				class="flex flex-col gap-2 rounded-md border p-4 shadow"
			>
				<div class="flex justify-between items-center text-sm text-gray-700">
					<div>M-Pesa Express Credentials</div>
					<Button @click="showAddMpesaDialog = true">Edit</Button>
				</div>
				<div class="overflow-hidden text-ellipsis text-base font-medium">
					<span class="font-normal text-gray-600">{{
						mpesaSetupId || 'Not Set'
					}}</span>
				</div>
			</div>

			<AddMpesaCredentials
				v-model="showAddMpesaDialog"
				@closeDialog="showAddMpesaDialog = false"
			/>
			<!-- End of M-Pesa Adding -->

			<!-- Add Payment Gateway -->
			<div class="flex flex-col gap-2 rounded-md border p-4 shadow">
				<div class="flex justify-between items-center text-sm text-gray-700">
					<div>Payment Gateway</div>
					<Button
						@click="showAddPaymentGatewayDialog = true"
						:disabled="!Boolean(mpesaSetupId)"
						>Edit</Button
					>
				</div>
				<div class="overflow-hidden text-ellipsis text-base font-medium">
					<span class="font-normal text-gray-600">{{
						paymentGatewayID || 'Not set'
					}}</span>
				</div>
			</div>
			<!-- End of Payment Gateway Adding -->

			<AddPaymentGateway
				v-model="showAddPaymentGatewayDialog"
				@closeDialog="showAddPaymentGatewayDialog = false"
			/>

			<!--Submit Payment Transaction To Frappe-->
			<div class="flex flex-col gap-2 rounded-md border p-4 shadow">
				<div class="flex justify-between items-center text-sm text-gray-700">
					<div>Partner Payment Payout</div>
					<Button @click="showPartnerPaymentPayout = true">Edit</Button>
				</div>
				<div class="overflow-hidden text-ellipsis text-base font-medium">
					<span class="font-normal text-gray-600">Not set</span>
				</div>
			</div>
			<!--End of payment transaction-->

			<!-- Parent Component -->
			<PartnerPaymentPayout
				v-model="showPartnerPaymentPayout"
				@closeDialog="showPartnerPaymentPayout = false"
			/>
		</div>
	</div>
</template>

<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'LocalPaymentSetup',
	components: {
		AddMpesaCredentials: defineAsyncComponent(
			() => import('../billing/mpesa/AddMpesaCredentials.vue'),
		),
		AddPaymentGateway: defineAsyncComponent(
			() => import('../billing/mpesa/AddPaymentGateway.vue'),
		),
		PartnerPaymentPayout: defineAsyncComponent(
			() => import('../billing/mpesa/PartnerPaymentPayout.vue'),
		),
	},
	data() {
		return {
			showAddMpesaDialog: false,
			showAddPaymobDialog: false,
			showAddPaymentGatewayDialog: false,
			showPartnerPaymentPayout: false,
			mpesaSetupId: '',
			paymentGatewayID: '',
		};
	},
	resources: {
		fetchLocalPaymentSetupDetails() {
			return {
				url: 'press.api.partner.get_local_payment_setup',
				onSuccess(data) {
					this.mpesaSetupId = data.mpesa_setup;
					this.paymentGatewayID = data.payment_gateway;
				},
				auto: true,
			};
		},
	},
};
</script>
