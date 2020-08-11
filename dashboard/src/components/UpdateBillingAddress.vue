<template>
	<Dialog title="Update Billing Address" v-model="show">
		<p class="text-base">
			Update your billing address so that we can show it in your monthly
			invoice.
		</p>
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
import AddressForm from '@/components/AddressForm';

export default {
	name: 'UpdateBillingAddress',
	components: {
		AddressForm
	},
	data() {
		return {
			show: true,
			billingInformation: {
				gstin: '',
				country: ''
			}
		};
	},
	resources: {
		updateBillingInformation() {
			return {
				method: 'press.api.account.update_billing_information',
				params: this.billingInformation,
				onSuccess() {
					this.show = false;
					this.$notify({
						title: 'Address updated successfully!'
					});
				},
				validate() {
					return this.$refs['address-form'].validateValues();
				}
			};
		}
	}
};
</script>
