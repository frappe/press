<template>
	<div
		class="text-sm cursor-pointer w-fit mb-4"
		v-on:click="$emit('update:step', 2)"
	>
		← Back to Plans
	</div>

	<ErrorMessage
		class="my-3 ml-6"
		:message="$resources.updateBillingDetails.error"
	/>
	<div class="flex flex-col justify-between px-6">
		<div>
			<Input
				class="mb-2"
				type="text"
				label="Billing Name"
				v-model="billingName"
				required
			/>
			<Input class="mb-2" label="Address" type="text" v-model="address" />
			<Input
				class="mb-2"
				label="Country"
				type="select"
				v-model="country"
				:options="countries"
				required
			/>
			<div class="flex flex-col justify-between sm:flex-row">
				<Input
					v-if="country === 'India'"
					class="mb-2 w-1/3"
					label="State/Province/Region"
					type="select"
					v-model="state"
					:options="indianStates"
					required
				/>
				<Input
					v-else
					class="mb-2"
					label="State/Province/Region"
					type="text"
					v-model="state"
					required
				/>
				<Input class="mb-2" label="City" type="text" v-model="city" />
				<Input
					class="mb-2"
					label="Postal Code"
					type="text"
					v-model="postalCode"
					required
				/>
			</div>

			<div v-show="currency === 'INR'">
				<span class="mb-2 block text-sm leading-4 text-gray-700">
					GSTIN(only for Indian customers)
				</span>
				<Input
					v-if="gstApplicable"
					type="text"
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
			appearance="primary"
			class="self-end mt-8"
			:loading="$resources.updateBillingDetails.loading"
			@click="$resources.updateBillingDetails.submit()"
		>
			Update Billing Details
		</Button>
	</div>
</template>

<script>
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
			indianStates: [
				'Andaman and Nicobar Islands',
				'Andhra Pradesh',
				'Arunachal Pradesh',
				'Assam',
				'Bihar',
				'Chandigarh',
				'Chhattisgarh',
				'Dadra and Nagar Haveli and Daman and Diu',
				'Delhi',
				'Goa',
				'Gujarat',
				'Haryana',
				'Himachal Pradesh',
				'Jammu and Kashmir',
				'Jharkhand',
				'Karnataka',
				'Kerala',
				'Ladakh',
				'Lakshadweep Islands',
				'Madhya Pradesh',
				'Maharashtra',
				'Manipur',
				'Meghalaya',
				'Mizoram',
				'Nagaland',
				'Odisha',
				'Other Territory',
				'Pondicherry',
				'Punjab',
				'Rajasthan',
				'Sikkim',
				'Tamil Nadu',
				'Telangana',
				'Tripura',
				'Uttar Pradesh',
				'Uttarakhand',
				'West Bengal'
			]
		};
	},
	resources: {
		updateBillingDetails() {
			return {
				method: 'press.api.developer.marketplace.update_billing_info',
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
	},
	methods: {}
};
</script>
