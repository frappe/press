<template>
	<FormControl class="mt-4" v-model="billing_name" label="Billing Name" />
	<Form
		class="mt-4"
		:fields="fields"
		:modelValue="billingInformation"
		@update:modelValue="data => Object.assign(billingInformation, data)"
		ref="address-form"
	></Form>
	<div class="mt-4" v-show="billingInformation.country == 'India'">
		<FormControl label="I have GSTIN" type="checkbox" v-model="gstApplicable" />
		<FormControl
			class="mt-2"
			label="GSTIN"
			v-if="gstApplicable"
			type="text"
			v-model="billingInformation.gstin"
			:disabled="!gstApplicable"
		/>
	</div>

	<ErrorMessage
		class="mt-2"
		:message="$resources.updateBillingInformation.error"
	/>
	<div class="flex w-full justify-end">
		<Button
			class="mt-3 w-full sm:w-fit"
			:class="{
				'sm:w-fit': !submitButtonWidthFull,
				'sm:w-full': submitButtonWidthFull
			}"
			variant="solid"
			:loading="$resources.updateBillingInformation.loading"
			@click="$resources.updateBillingInformation.submit"
		>
			{{ submitButtonText }}
		</Button>
	</div>
</template>

<script>
import { indianStates } from '@/utils/billing.js';

import { DashboardError } from '../../utils/error';
import { toast } from 'vue-sonner';

export default {
	name: 'UpdateAddressForm',
	emits: ['updated'],
	inject: ['team'],
	components: {
		Form: () => import('@/components/Form.vue')
	},
	props: {
		submitButtonText: {
			default: 'Update Billing Details'
		},
		submitButtonWidthFull: {
			default: false
		}
	},
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
			url: 'press.saas.api.billing.country_list',
			auto: true,
			onSuccess() {
				let userCountry = this.team?.data.country;
				if (userCountry) {
					let country = this.countryList.find(d => d.label === userCountry);
					if (country) {
						this.updateAddress('country', country.value);
					}
				}
			}
		},
		validateGST() {
			return {
				url: 'press.saas.api.billing.validate_gst',
				makeParams() {
					return {
						address: this.billingInformation
					};
				}
			};
		},
		currentBillingInformation() {
			return {
				url: 'press.saas.api.billing.get_information',
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
									: billingInformation.gstin
						});
						this.billing_name = billingInformation.billing_name;
					}
				}
			};
		},
		updateBillingInformation() {
			return {
				url: 'press.saas.api.billing.update_information',
				makeParams() {
					return {
						billing_details: {
							...this.billingInformation,
							billing_name: this.billing_name
						}
					};
				},
				onSuccess() {
					toast.success('Address updated successfully!');
					this.$emit('updated');
				},
				validate() {
					var billing_name = this.billing_name.trim();
					if (!billing_name) {
						throw new DashboardError('Billing Name is required');
					}
					var billingNameRegex = /^[a-zA-Z0-9\-\'\,\.\s]+$/;
					var billingNameValid = billingNameRegex.test(billing_name);
					if (!billingNameValid) {
						throw new DashboardError(
							'Billing Name contains invalid characters'
						);
					}
					this.billing_name = billing_name;
					return this.validateValues();
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
					fieldtype:
						this.billingInformation.country === 'India' ? 'Select' : 'Data',
					label: 'State / Province / Region',
					fieldname: 'state',
					required: 1,
					options:
						this.billingInformation.country === 'India'
							? this.indianStates
							: null
				},
				{
					fieldtype: 'Data',
					label: 'Postal Code',
					fieldname: 'postal_code',
					required: 1
				}
			];
		}
	},
	methods: {
		updateAddress(key, value) {
			this.billingInformation = {
				...this.billingInformation,
				[key]: value
			};
		},
		async validateValues() {
			let { country } = this.billingInformation;
			let is_india = country == 'India';
			let values = this.fields
				.flat()
				.filter(df => df.fieldname != 'gstin' || is_india)
				.map(df => this.billingInformation[df.fieldname]);

			if (!values.every(Boolean)) {
				throw new DashboardError('Please fill required values');
			}

			try {
				await this.validateGST();
			} catch (error) {
				console.log(error);
				throw new DashboardError(error.messages?.join('\n'));
			}
		},
		async validateGST() {
			this.updateAddress(
				'gstin',
				this.gstApplicable ? this.billingInformation.gstin : 'Not Applicable'
			);
			await this.$resources.validateGST.submit();
		}
	}
};
</script>
