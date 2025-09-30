<template>
	<FormControl class="mt-4" v-model="billing_name" label="Billing Name" />
	<AddressForm
		ref="address-form"
		class="mt-4"
		v-model:address="billingInformation"
	/>
	<ErrorMessage
		class="mt-2"
		:message="$resources.updateBillingInformation.error"
	/>
	<div class="flex w-full justify-end">
		<Button
			class="mt-2 w-full sm:w-fit"
			variant="solid"
			:loading="$resources.updateBillingInformation.loading"
			@click="$resources.updateBillingInformation.submit"
		>
			Update Billing Details
		</Button>
	</div>
</template>

<script>
import { DashboardError } from '../utils/error';
import AddressForm from './AddressForm.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'UpdateBillingDetailsForm',
	emits: ['updated'],
	components: {
		AddressForm,
	},
	data() {
		return {
			billing_name: '',
			billingInformation: {
				address: '',
				city: '',
				state: '',
				postal_code: '',
				country: '',
				gstin: '',
			},
		};
	},
	resources: {
		currentBillingInformation() {
			return {
				url: 'press.api.account.get_billing_information',
				auto: true,
				onSuccess(billingInformation) {
					if ('country' in (billingInformation || {})) {
						Object.assign(this.billingInformation, {
							address: billingInformation.address_line1,
							city: billingInformation.city,
							state: billingInformation.state,
							postal_code: billingInformation.pincode,
							country: billingInformation.country,
							gstin:
								billingInformation.gstin == 'Not Applicable'
									? ''
									: billingInformation.gstin,
						});
						this.billing_name = billingInformation.billing_name;
					}
				},
			};
		},
		updateBillingInformation() {
			return {
				url: 'press.api.account.update_billing_information',
				makeParams() {
					return {
						billing_details: {
							...this.billingInformation,
							billing_name: this.billingInformation.billing_name,
						},
					};
				},
				onSuccess() {
					toast.success('Address updated successfully!');
					this.$emit('updated');
				},
				validate() {
					var billing_name = this.billing_name.trim();
					var billingNameRegex = /^[a-zA-Z0-9\-\'\,\.\s]+$/;
					var billingNameValid = billingNameRegex.test(billing_name);
					if (!billingNameValid) {
						throw new DashboardError(
							'Billing Name contains invalid characters',
						);
					}
					this.billing_name = billing_name;
					return this.$refs['address-form'].validateValues();
				},
			};
		},
	},
};
</script>
