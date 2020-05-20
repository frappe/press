<template>
	<div class="p-8">
		<h1 class="text-xl font-semibold">
			Welcome to Frappe Cloud
		</h1>
		<p>
			To start using Frappe Cloud, complete the following steps to get your
			account up and running.
		</p>
		<SectionCard class="mt-6">
			<div class="-mt-2"></div>
			<div class="divide-y">
				<button
					class="flex items-start w-full px-6 py-4 cursor-pointer focus:outline-none focus:shadow-outline"
					:class="{
						'bg-green-50 text-green-700': step.done,
						'hover:bg-blue-50': step.nextStep,
						'cursor-not-allowed': !step.done && !step.nextStep
					}"
					v-show="step.show"
					v-for="step in steps"
					:key="step.name"
					:disabled="step.done || !step.nextStep || step.disabled"
					@click="step.nextStep ? step.click() : null"
				>
					<FeatherIcon
						:name="step.done ? 'check' : step.icon"
						:stroke-width="step.done ? 4 : 2"
						class="flex-shrink-0 w-4 h-4 my-1"
					/>
					<div class="ml-4 text-left">
						<div class="font-medium">
							{{ step.name }}
						</div>
						<div
							class="mt-1 text-sm"
							:class="step.done ? 'text-green-800 opacity-75' : 'text-gray-800'"
						>
							{{ step.description }}
						</div>
					</div>
				</button>
			</div>
			<div class="-mb-2"></div>
		</SectionCard>
		<div class="mt-4" v-if="onboardingComplete">
			Onboarding Complete! Redirecting to sites...
		</div>
		<Dialog title="Add Billing Information" v-model="showAddCardDialog">
			<StripeCard
				v-if="showAddCardDialog"
				class="mb-1"
				@complete="afterCardAdd"
			/>
		</Dialog>
		<Dialog title="Update Billing Address" v-model="showAddressDialog">
			<p>
				Add your billing address so that we can show it in your monthly invoice.
			</p>
			<Form class="mt-4" :fields="addressFields" v-model="billingInformation" />
			<template slot="actions">
				<Button
					type="primary"
					@click="updateBillingInformation.submit()"
					:loading="updateBillingInformation.loading"
					:disabled="!billingInformationValid"
				>
					Submit
				</Button>
			</template>
		</Dialog>
	</div>
</template>

<script>
import StripeCard from '@/components/StripeCard';
import Dialog from '@/components/Dialog';
import Form from '@/components/Form';

export default {
	name: 'Welcome',
	components: {
		StripeCard,
		Dialog,
		Form
	},
	resources: {
		onboarding: {
			method: 'press.api.account.onboarding',
			auto: true,
			onSuccess(onboarding) {
				let foundNextStep = false;
				this.steps = this.steps.map(step => {
					let obj = onboarding[step.name];
					Object.assign(step, obj);
					if (!foundNextStep && !step.done) {
						step.nextStep = true;
						foundNextStep = true;
					} else {
						step.nextStep = false;
					}
					return step;
				});

				let addressStep = this.steps.find(
					d => d.name == 'Update Billing Address'
				);
				if (addressStep.show && !addressStep.done) {
					this.showAddressDialog = true;
				}

				this.onboardingComplete = onboarding.complete;
				if (this.onboardingComplete) {
					setTimeout(() => {
						this.$router.replace('/sites');
					}, 2000);
				}
			}
		},
		updateBillingInformation() {
			return {
				method: 'press.api.account.update_billing_information',
				params: this.billingInformation,
				onSuccess() {
					this.showAddressDialog = false;
					this.$resources.onboarding.reload();
				}
			};
		}
	},
	data() {
		let team = this.$store.account.team?.name || '';
		return {
			showAddCardDialog: false,
			onboardingComplete: false,
			showAddressDialog: false,
			billingInformation: {},
			countryList: [],
			steps: [
				{
					name: 'Create a Team',
					done: true,
					show: true,
					icon: '',
					description: `Your team ${team} has been created.`
				},
				{
					name: 'Add Billing Information',
					description:
						"After adding your billing information you will get a free $25 credit. Sites you create will use your free credits first. If you don't like the experience you can cancel your subscription anytime.",
					done: false,
					show: true,
					icon: 'credit-card',
					click: () => {
						this.showAddCardDialog = true;
					},
					disabled: false
				},
				{
					name: 'Update Billing Address',
					description:
						'Add your billing address so that we can show it in your monthly invoice.',
					done: false,
					show: false,
					icon: 'map',
					click: () => {
						this.showAddressDialog = true;
					},
					disabled: false
				},
				{
					name: 'Create your first site',
					done: false,
					show: true,
					icon: 'plus-circle',
					description:
						'Creating a new site is as easy as choosing a subdomain and a plan.',
					click: () => {
						this.$router.push('/sites/new');
					}
				}
			]
		};
	},
	async mounted() {
		let countryList = await this.$call('frappe.client.get_list', {
			doctype: 'Country',
			fields: 'name, code',
			limit_page_length: null
		});
		this.countryList = [{ label: 'Select Country', value: '' }].concat(
			countryList.map(d => ({
				label: d.name,
				value: d.code
			}))
		);
		let country = this.countryList.find(
			d => d.label === this.$store.account.team.country
		);
		if (country) {
			this.billingInformation.country = country.value;
		}
	},
	methods: {
		afterCardAdd() {
			this.showAddCardDialog = false;
			this.reloadUntilAddCardIsTrue();
		},
		async reloadUntilAddCardIsTrue() {
			let cardStep = this.steps.find(d => d.name === 'Add Billing Information');
			if (!cardStep.done) {
				cardStep.disabled = true;
				await this.$resources.onboarding.reload();
				setTimeout(() => {
					this.reloadUntilAddCardIsTrue();
				}, 1000);
			} else {
				cardStep.disabled = false;
			}
		}
	},
	computed: {
		billingInformationValid() {
			return this.addressFields
				.map(df => this.billingInformation[df.fieldname])
				.every(Boolean);
		},
		addressFields() {
			return [
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
					fieldtype: 'Data',
					label: 'State',
					fieldname: 'state',
					required: 1
				},
				{
					fieldtype: 'Data',
					label: 'Postal Code',
					fieldname: 'postal_code',
					required: 1
				},
				{
					fieldtype: 'Select',
					label: 'Country',
					fieldname: 'country',
					options: this.countryList,
					required: 1
				}
			];
		}
	}
};
</script>
