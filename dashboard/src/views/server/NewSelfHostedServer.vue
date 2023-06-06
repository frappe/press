<template>
	<WizardCard v-if="options">
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Create a new Self Hosted Server</h1>
		</div>
		<Steps :steps="steps">
			<template v-slot="{ active: activeStep, next, previous, hasPrevious, hasNext }">
				<div class="mt-8"></div>
				<SelfHostedHostname v-show="activeStep.name === 'SelfHostedHostname'" v-model:title="title"
					v-model:domain="domain" />
				<div>
					<SelfHostedServerForm v-show="activeStep.name === 'ServerDetails'" v-model:publicIP="publicIP"
						v-model:privateIP="privateIP" v-model:error="ipInvalid" />
					<Button appearance="primary"
						v-show="activeStep.name === 'ServerDetails' && !this.ipInvalid && this.domain"
						@click="!domainVerified && $resources.verifyDNS.submit()" :loading="$resources.verifyDNS.loading"
						:icon-left="domainVerified ? 'check' : ''">
						{{ domainVerified ? "Domain Verified" : "Verify Domain" }}
					</Button>
				</div>
				<div class="mt-4">
					<SelfHostedServerPlan v-model:selectedPlan="selectedPlan" :options="options"
						v-show="activeStep.name === 'SelfHostedServerPlan'" />
				</div>
				<div class="mt-4">
					<SelfHostedServerVerify v-show="activeStep.name === 'VerifyServer'" v-model:ssh_key="ssh_key" />

					<Button v-show="activeStep.name === 'VerifyServer' && !playOutput && !unreachable
						" @click="$resources.verify.submit()" :loading="$resources.verify.loading" appearance="primary">
						Verify Server
					</Button>
					<Button v-show="activeStep.name === 'VerifyServer' && playOutput" icon-left="check"
						appearance="primary">
						Server Verified
					</Button>
					<Button v-show="activeStep.name === 'VerifyServer' && unreachable" icon-left="x" appearance="danger"
						:loading="$resources.verify.loading" @click="$resources.verify.submit()">
						Server Unreachable
					</Button>
				</div>
				<ErrorMessage :message="validationMessage" />
				<div class="mt-4">
					<!-- Region consent checkbox -->
					<div class="my-6" v-if="!hasNext">
						<Input id="region-consent" type="checkbox" label="I agree that the laws of the region selected by me shall stand
							applicable to me and Frappe." class="rounded border-gray-300 focus:ring-blue-500"
							v-model="agreedToRegionConsent" />
					</div>
					<ErrorMessage class="mb-4" :message="$resources.newServer.error" />

					<div class="flex justify-between">
						<Button @click="previous" :class="{
								'pointer-events-none opacity-0': !hasPrevious
							}">
							Back
						</Button>

						<Button appearance="primary" @click="nextStep(activeStep, next)"
							:disabled="activeStep.name === 'ServerDetails' ? !domainVerified : false" :class="{
									'pointer-events-none opacity-0': !hasNext
								}">
							Next
						</Button>
						<Button v-show="!hasNext" appearance="primary"
							:disabled="!playOutput || !this.agreedToRegionConsent" @click="setupServers"
							:loading="$resources.setupServer.loading">
							Setup Server
						</Button>
					</div>
				</div>
			</template>
		</Steps>
	</WizardCard>
</template>

<script>
import WizardCard from '@/components/WizardCard.vue';
import Steps from '@/components/Steps.vue';
import SelfHostedHostname from './NewSelfHostedServerHostname.vue';
import SelfHostedServerForm from './NewSelfHostedServerForm.vue';
import SelfHostedServerVerify from './SelfHostedServerVerify.vue';
import SelfHostedServerPlan from './SelfHostedServerPlan.vue';
export default {
	name: 'NewSelfHostedServer',
	components: {
		WizardCard,
		Steps,
		SelfHostedHostname,
		SelfHostedServerPlan,
		SelfHostedServerForm,
		SelfHostedServerVerify,
	},
	data() {
		return {
			title: null,
			options: null,
			publicIP: null,
			privateIP: null,
			validationMessage: null,
			serverDoc: null,
			playID: null,
			ssh_key: null,
			selectedPlan: null,
			domain: null,
			ipInvalid: false,
			playStatus: false,
			unreachable: false,
			playOutput: false,
			agreedToRegionConsent: false,
			domainVerified: false,
			steps: [
				{
					name: 'SelfHostedHostname',
					validate: () => {
						return this.title && this.domain;
					}
				},
				{
					name: 'ServerDetails',
					validate: () => {
						return this.privateIP && this.publicIP;
					}
				},
				{
					name: 'SelfHostedServerPlan',
					validate: () => {
						return this.selectedPlan;
					}
				},
				{
					name: 'VerifyServer',
					validate: () => {
						return this.playOutput;
					}
				}
			],
		};
	},
	async mounted() {
		const plans = await this.$call('press.api.selfhosted.get_plans');
		this.options = plans.map(plan => {
			plan.disabled = !this.$account.hasBillingInfo;
			plan.vcpu = "Any"
			return plan;
		});
		this.ssh_key = await this.$call('press.api.selfhosted.sshkey');
	},
	resources: {
		newServer() {
			return {
				method: 'press.api.selfhosted.new',
				params: {
					server: {
						title: this.title,
						publicIP: this.publicIP,
						privateIP: this.privateIP
					}
				},
				onSuccess(data) {
					this.serverDoc = data;
				},
				validate() {
					let canCreate = this.title && this.privateIP && this.publicIP;

					// if (!this.agreedToRegionConsent) {
					// 	// document.getElementById('region-consent').focus();

					// 	return 'Please agree to the above consent to create server';
					// }
					if (!canCreate) {
						return 'Cannot create server';
					}
				}
			};
		},
		verify() {
			return {
				method: 'press.api.selfhosted.verify',
				params: {
					server: "ss5.athul.fc.frappe.dev"
				},
				onSuccess(data) {
					if (data) {
						this.playOutput = true;
						this.unreachable = false;
					} else {
						this.playOutput = false;
						this.unreachable = true;
					}
				}
			};
		},
		setupServer() {
			return {
				method: 'press.api.selfhosted.setup',
				params: {
					server: this.serverDoc
				},
				validate() {
					let canCreate = this.title;

					if (!this.agreedToRegionConsent) {
						// document.getElementById('region-consent').focus();

						return 'Please agree to the above consent to create server';
					}
					if (!canCreate) {
						return 'Cannot create server';
					}
				}
			};
		},
		verifyDNS() {
			return {
				method: 'press.api.selfhosted.check_dns',
				params: {
					domain: this.domain,
					ip: this.publicIP
				},
				onSuccess(data) {
					this.domainVerified = data
				}
			}
		}
	},
	computed: {},
	methods: {
		async nextStep(activeStep, next) {
			if (activeStep.name === 'ServerDetails' && this.ipInvalid) {
				this.$resources.newServer.submit();
			}
			next();
		},
		async setupServers() {
			await this.$resources.setupServer.submit();
			if (this.agreedToRegionConsent) {
				this.$router.replace(`/servers/${this.serverDoc}/overview`);
			}
		},
	}
};
</script>
