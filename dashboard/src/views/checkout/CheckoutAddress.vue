<template>
	<div
		class="mb-4 w-fit cursor-pointer text-sm"
		v-on:click="$emit('update:step', 1)"
	>
		← Back to Plans
	</div>

	<ErrorMessage
		class="my-3 ml-6"
		:message="$resources.updateBillingDetails.error"
	/>
	<div class="flex flex-col justify-between px-6">
		<div>
			<FormControl
				class="mb-2"
				label="Billing Name"
				v-model="billingName"
				required
			/>
			<FormControl class="mb-2" label="Address" v-model="address" />
			<FormControl
				class="mb-2"
				label="Country"
				type="select"
				v-model="country"
				:options="countries"
				required
			/>
			<div class="flex flex-col justify-between sm:flex-row">
				<FormControl
					v-if="country === 'India'"
					class="mb-2 w-1/3"
					label="State/Province/Region"
					type="select"
					v-model="state"
					:options="indianStates"
					required
				/>
				<FormControl
					v-else
					class="mb-2"
					label="State/Province/Region"
					v-model="state"
					required
				/>
				<FormControl class="mb-2" label="City" type="text" v-model="city" />
				<FormControl
					class="mb-2"
					label="Postal Code"
					v-model="postalCode"
					required
				/>
			</div>

			<div v-show="currency === 'INR'">
				<span class="mb-2 block text-sm leading-4 text-gray-700">
					GSTIN(only for Indian customers)
				</span>
				<FormControl
					v-if="gstApplicable"
					v-model="gstin"
					:disabled="!gstApplicable"
				/>
				<Button
					v-if="gstApplicable"
					class="mt-2"
					@click="
						gstApplicable = false;
						gstin = 'Not Applicable';
					"
				>
					I don't have a GSTIN
				</Button>
				<Button
					v-else
					class="mt-2"
					@click="
						gstApplicable = true;
						gstin = '';
					"
				>
					Add a GSTIN
				</Button>
			</div>
		</div>
		<Button
			variant="solid"
			class="mt-8 self-end"
			:loading="$resources.updateBillingDetails.loading"
			@click="$resources.updateBillingDetails.submit()"
		>
			Update Billing Details
		</Button>
	</div>
</template>

<script>
import { indianStates } from '@/utils/billing';

export default {
	name: 'CheckoutAddress',
	props: ['currency', 'countries', 'secretKey', 'step'],
	data() {
		return {
			billingName: '',
			address: '',
			country: '',
			state: '',
			city: '',
			postalCode: null,
			gstin: 'Not Applicable',
			gstApplicable: false,
			indianStates: indianStates
		};
	},
	resources: {
		updateBillingDetails() {
			return {
				url: 'press.api.developer.marketplace.update_billing_info',
				params: {
					secret_key: this.secretKey,
					data: {
						billing_name: this.billingName,
						address: this.address,
						country: this.country,
						city: this.city,
						state: this.state,
						postal_code: this.postalCode,
						gstin: this.gstin
					}
				},
				onSuccess(r) {
					this.$emit('update:step', 4);
				}
			};
		}
	}
};
</script>
