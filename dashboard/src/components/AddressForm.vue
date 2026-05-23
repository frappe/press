<template>
	<div>
		<Form
			class="mt-4"
			:fields="fields"
			:modelValue="address"
			@update:modelValue="$emit('update:address', $event)"
		/>
		<div class="mt-4" v-show="address.country == 'Algeria'">
			<FormControl
				label="I have NIF"
				type="checkbox"
				v-model="gstApplicable"
			/>
			<FormControl
				class="mt-2"
				label="NIF"
				v-if="gstApplicable"
				type="text"
				v-model="address.gstin"
				:disabled="!gstApplicable"
			/>
		</div>
	</div>
</template>

<script>
import Form from '@/components/Form.vue';
import { algerianWilayas } from '@/utils/billing.js';
import { DashboardError } from '../utils/error';

export default {
	name: 'AddressForm',
	props: ['address'],
	emits: ['update:address'],
	components: {
		Form,
	},
	data() {
		return {
			gstApplicable: false,
		};
	},
	mounted() {
		if (this.address?.gstin && this.address.gstin !== 'Not Applicable') {
			this.gstApplicable = true;
		} else {
			this.update('gstin', 'Not Applicable');
		}
	},
	watch: {
		'address.gstin'(gstin) {
			this.update('gstin', gstin);
		},
		gstApplicable(gstApplicable) {
			if (gstApplicable) {
				this.update(
					'gstin',
					this.address.gstin === 'Not Applicable' ? '' : this.address.gstin,
				);
			} else {
				this.update('gstin', 'Not Applicable');
			}
		},
	},
	resources: {
		countryList: {
			url: 'press.api.account.country_list',
			auto: true,
			onSuccess() {
				let userCountry = this.$team?.doc.country;
				if (userCountry) {
					let country = this.countryList.find((d) => d.label === userCountry);
					if (country) {
						this.update('country', country.value);
					}
				}
			},
		},
		validateNIF() {
			return {
				url: 'press.api.billing.validate_gst',
				makeParams() {
					return {
						address: this.address,
					};
				},
			};
		},
	},
	methods: {
		update(key, value) {
			this.$emit('update:address', {
				...this.address,
				[key]: value,
			});
		},
		async validateNIF() {
			this.update(
				'gstin',
				this.gstApplicable ? this.address.gstin : 'Not Applicable',
			);
			await this.$resources.validateNIF.submit();
		},
		async validateValues() {
			let { country } = this.address;
			let is_algeria = country == 'Algeria';
			let values = this.fields
				.flat()
				.filter((df) => df.fieldname != 'gstin' || is_algeria)
				.map((df) => this.address[df.fieldname]);

			if (!values.every(Boolean)) {
				throw new DashboardError('Please fill required values');
			}

			try {
				await this.validateNIF();
			} catch (error) {
				throw new DashboardError(error.messages?.join('\n'));
			}
		},
	},
	computed: {
		countryList() {
			return (this.$resources.countryList.data || []).map((d) => ({
				label: d.name,
				value: d.name,
			}));
		},
		algerianWilayas() {
			return algerianWilayas.map((d) => ({
				label: d,
				value: d,
			}));
		},
		fields() {
			return [
				{
					fieldtype: 'Select',
					label: 'Country',
					fieldname: 'country',
					options: this.countryList,
					required: 1,
				},
				{
					fieldtype: 'Data',
					label: 'Address',
					fieldname: 'address',
					required: 1,
				},
				{
					fieldtype: 'Data',
					label: 'City',
					fieldname: 'city',
					required: 1,
				},
				{
					fieldtype: this.address.country === 'Algeria' ? 'Select' : 'Data',
					label: 'State / Province / Region',
					fieldname: 'state',
					required: 1,
					options: this.address.country === 'Algeria' ? this.algerianWilayas : null,
				},
				{
					fieldtype: 'Data',
					label: 'Postal Code',
					fieldname: 'postal_code',
					required: 1,
				},
			];
		},
	},
};
</script>
