<template>
	<FormControl class="mt-4" v-model="billing_name" label="Billing Name" />
	<!-- <AddressForm
		ref="address-form"
		class="mt-4"
		v-model:address="billingInformation"
	/> -->
	<Form
		class="mt-4"
		:fields="fields"
		:modelValue="address"
		@update:modelValue="$emit('update:address', $event)"
	/>
	<div class="mt-4" v-show="address.country == 'India'">
		<FormControl label="I have GSTIN" type="checkbox" v-model="gstApplicable" />
		<FormControl
			class="mt-2"
			label="GSTIN"
			v-if="gstApplicable"
			type="text"
			v-model="address.gstin"
			:disabled="!gstApplicable"
		/>
	</div>

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
import Form from '@/components/Form.vue';
import { indianStates } from '@/utils/billing.js';

import { DashboardError } from '../../utils/error';
import { notify } from '@/utils/toast.js';

export default {
	name: 'UpdateAddressForm',
	emits: ['updated'],
	components: {},
	data() {
		return {
			gstApplicable: false,
			billing_name: '',
			billingInformation: {
				address: '',
				city: '',
				state: '',
				postal_code: '',
				country: '',
				gstin: ''
			}
		};
	},
	resources: {
		countryList: {
			url: 'press.api.account.country_list',
			auto: true,
			onSuccess() {
				// TODO: remove this.$account usage after dashboard-beta is merged
				// let userCountry =
				// 	this.$account?.team.country || this.$team?.doc.country;
				let userCountry = 'India';
				if (userCountry) {
					let country = this.countryList.find(d => d.label === userCountry);
					if (country) {
						this.update('country', country.value);
					}
				}
			}
		},
		validateGST() {
			return {
				url: 'press.api.billing.validate_gst',
				makeParams() {
					return {
						address: this.address
					};
				}
			};
		},
		currentBillingInformation() {
			return {
				url: 'press.api.account.get_billing_information',
				auto: false,
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
									: billingInformation.gstin
						});
						this.billing_name = billingInformation.billing_name;
					}
				}
			};
		},
		updateBillingInformation() {
			return {
				url: 'press.api.account.update_billing_information',
				makeParams() {
					return {
						billing_details: {
							...this.billingInformation,
							billing_name: this.billingInformation.billing_name
						}
					};
				},
				onSuccess() {
					notify({
						title: 'Address updated successfully!'
					});
					this.$emit('updated');
				},
				validate() {
					var billing_name = this.billing_name.trim();
					var billingNameRegex = /^[a-zA-Z0-9\-\'\,\.\s]+$/;
					var billingNameValid = billingNameRegex.test(billing_name);
					if (!billingNameValid) {
						throw new DashboardError(
							'Billing Name contains invalid characters'
						);
					}
					this.billing_name = billing_name;
					return this.$refs['address-form'].validateValues();
				}
			};
		}
	},
	computed: {
		countryList() {
			return (this.$resources.countryList.data || []).map(d => ({
				label: d.name,
				value: d.name
			}));
		},
		indianStates() {
			return indianStates.map(d => ({
				label: d,
				value: d
			}));
		},
		fields() {
			return [
				{
					fieldtype: 'Select',
					label: 'Country',
					fieldname: 'country',
					options: this.countryList,
					required: 1
				},
				{
					fieldtype: 'Data',
					label: 'Address',
					fieldname: 'address',
					required: 1
				},
				{
					fieldtype: 'Data',
					label: 'City',
					fieldname: 'city',
					required: 1
				},
				{
					fieldtype: this.address.country === 'India' ? 'Select' : 'Data',
					label: 'State / Province / Region',
					fieldname: 'state',
					required: 1,
					options: this.address.country === 'India' ? this.indianStates : null
				},
				{
					fieldtype: 'Data',
					label: 'Postal Code',
					fieldname: 'postal_code',
					required: 1
				}
			];
		}
	}
};
</script>
