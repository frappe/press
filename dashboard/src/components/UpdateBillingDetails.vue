<template>
	<Dialog
		:options="{
			title: 'Update Billing Address',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					loading: $resources.updateBillingInformation.loading,
					onClick: () => $resources.updateBillingInformation.submit(),
				},
			],
		}"
		:modelValue="show"
		@update:modelValue="$emit('update:show', $event)"
	>
		<template v-slot:body-content>
			<p class="mb-5 text-sm text-ink-gray-7" v-if="message">
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
import { toast } from 'vue-sonner'
import { validateBillingName } from '../utils/billing'
import { DashboardError } from '../utils/error'
import AddressForm from './AddressForm.vue'

export default {
	name: 'UpdateBillingDetails',
	props: ['message', 'show'],
	emits: ['update:show', 'updated'],
	components: {
		AddressForm,
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
				billing_name: '',
			},
		}
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
							billing_name: billingInformation.billing_name,
						})
					}
				},
			}
		},
		updateBillingInformation() {
			return {
				url: 'press.api.account.update_billing_information',
				makeParams() {
					return {
						billing_details: this.billingInformation,
					}
				},
				onSuccess() {
					this.$emit('update:show', false)
					toast.success('Address updated successfully!')
					this.$emit('updated')
				},
				validate() {
					const billing_name = validateBillingName(
						this.billingInformation.billing_name,
					)
					if (!billing_name) {
						throw new DashboardError('Billing Name contains invalid characters')
					}
					this.billingInformation.billing_name = billing_name
					return this.$refs['address-form'].validateValues()
				},
			}
		},
	},
}
</script>
