<template>
	<Dialog
		title="Update Billing Details"
		:show="show"
		@change="value => $emit('change', value)"
	>
		<p class="text-base" v-if="message">
			{{ message }}
		</p>
		<Input
			class="pt-4"
			type="text"
			v-model="billingInformation.billing_name"
			label="Billing Name"
		/>
		<AddressForm ref="address-form" class="mt-4" v-model="billingInformation" />
		<ErrorMessage
			class="mt-2"
			:error="$resources.updateBillingInformation.error"
		/>
		<template slot="actions">
			<Button
				type="primary"
				@click="updateBillingInformation.submit()"
				:loading="updateBillingInformation.loading"
			>
				Submit
			</Button>
		</template>
	</Dialog>
</template>

<script>
import AddressForm from '@/components/AddressForm.vue';

export default {
	name: 'UpdateBillingDetails',
	props: ['message', 'show'],
	model: {
		prop: 'show',
		event: 'change'
	},
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
			method: 'press.api.account.get_billing_information',
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
				method: 'press.api.account.update_billing_information',
				params: {
					billing_details: this.billingInformation
				},
				onSuccess() {
					this.$emit('change', false);
					this.$notify({
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
