<template>
	<Dialog
		:options="{
			title: 'Update Billing Details',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					loading: $resources.updateBillingInformation.loading,
					onClick: () => $resources.updateBillingInformation.submit()
				}
			]
		}"
		:modelValue="show"
		@update:modelValue="$emit('update:show', $event)"
	>
		<template v-slot:body-content>
			<p class="text-base" v-if="message">
				{{ message }}
			</p>
			<FormControl
				class="mt-4"
				v-model="billingInformation.billing_name"
				label="Billing Name"
			/>
			<AddressForm
				ref="address-form"
				class="mt-4"
				v-model:address="billingInformation"
			/>
			<ErrorMessage
				class="mt-2"
				:message="$resources.updateBillingInformation.error"
			/>
		</template>
	</Dialog>
</template>

<script>
import AddressForm from '@/components/AddressForm.vue';
import { notify } from '@/utils/toast';

export default {
	name: 'UpdateBillingDetails',
	props: ['message', 'show'],
	emits: ['update:show', 'updated'],
	components: {
		AddressForm
	},
	data() {
		return {
			billingInformation: {
				address: '',
				city: '',
				state: '',
				postal_code: '',
				country: '',
				gstin: '',
				billing_name: ''
			}
		};
	},
	resources: {
		currentBillingInformation: {
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
						billing_name: billingInformation.billing_name
					});
				}
			}
		},
		updateBillingInformation() {
			return {
				url: 'press.api.account.update_billing_information',
				params: {
					billing_details: this.billingInformation
				},
				onSuccess() {
					this.$emit('update:show', false);
					notify({
						title: 'Address updated successfully!'
					});
					this.$emit('updated');
				},
				validate() {
					return this.$refs['address-form'].validateValues();
				}
			};
		}
	}
};
</script>
