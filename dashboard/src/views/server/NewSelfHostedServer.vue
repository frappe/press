<template>
	<WizardCard v-if="options">
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Create a new Self Hosted Server</h1>
		</div>
		<Steps :steps="steps">
			<template
				v-slot="{ active: activeStep, next, previous, hasPrevious, hasNext }"
			>
				<div class="mt-8"></div>
				<SelfHostedHostname
					:options="options"
					v-show="activeStep.name === 'SelfHostedHostname'"
					v-model:title="title"
				/>
				<div>
					<SelfHostedServerForm
						v-show="activeStep.name === 'ServerDetails'"
						v-model:publicIP="publicIP"
						v-model:privateIP="privateIP"
						v-model:error="ipValidationMessage"
					/>
				</div>
				<div class="mt-4">
					<SelfHostedServerVerify
						v-show="activeStep.name === 'VerifyServer'"
						v-model:ssh_key="ssh_key"
					/>

					<Button
						v-show="
							activeStep.name === 'VerifyServer' && !playOutput && !unreachable
						"
						:loading="playStatus"
						appearance="primary"
						@click="startVerification"
						>
						Verify Server
						</Button>
					<Button
						v-show="activeStep.name === 'VerifyServer' && playOutput"
						icon-left="check"
						appearance="primary"
						:loading="playStatus"
						@click="startVerification"
					>
					Server Verified
					</Button>
					<Button
						v-show="activeStep.name === 'VerifyServer' && unreachable"
						icon-left="x"
						appearance="danger"
						:loading="playStatus"
						@click="startVerification"
					>
					Server Unreachable
					</Button>
				</div>
				<ErrorMessage :message="validationMessage" />
				<div class="mt-4">
					<!-- Region consent checkbox -->
					<div class="my-6" v-if="!hasNext">
						<input
							id="region-consent"
							type="checkbox"
							class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
							v-model="agreedToRegionConsent"
						/>
						<label
							for="region-consent"
							class="ml-1 text-sm font-semibold text-gray-900"
						>
							I agree that the laws of the region selected by me shall stand
							applicable to me and Frappe.
						</label>
					</div>
					<ErrorMessage class="mb-4" :message="$resources.newServer.error" />

					<div class="flex justify-between">
						<Button
							@click="previous"
							:class="{
								'pointer-events-none opacity-0': !hasPrevious
							}"
						>
							Back
						</Button>
						<Button
							appearance="primary"
							@click="nextStep(activeStep, next)"
							:class="{
								'pointer-events-none opacity-0': !hasNext
							}"
						>
							Next
						</Button>
						<Button
							v-show="!hasNext"
							appearance="primary"
							:disabled='!playOutput'
							@click="setupServers"
							:loading="$resources.setupServer.loading"
						>
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
export default {
	name: 'NewSelfHostedServer',
	components: {
		WizardCard,
		Steps,
		SelfHostedHostname,
		SelfHostedServerForm,
		SelfHostedServerVerify
	},
	data() {
		return {
			title: null,
			options: null,
			publicIP: null,
			privateIP: null,
			validationMessage: null,
			ipValidationMessage: null,
			serverDoc: null,
			playID: null,
			playStatus: false,
			unreachable: false,
			ssh_key: null,
			steps: [
				{
					name: 'SelfHostedHostname',
					validate: () => {
						return this.title;
					}
				},
				{
					name: 'ServerDetails',
					validate: () => {
						if (this.verifyIP(this.privateIP) && this.verifyIP(this.publicIP)) {
							return this.privateIP && this.publicIP;
						} else {
							this.ipValidationMessage = 'Please enter valid IP addresses';
						}
					}
				},
				{
					name: 'VerifyServer',
					validate: () => {
						return this.playOutput;
					}
				}
			],
			playOutput: false,
			agreedToRegionConsent: false
		};
	},
	async mounted() {
		this.options = await this.$call('press.api.server.options', {
			type: 'self_hosted'
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
				}
			};
		},
		verify() {
			return {
				method: 'press.api.selfhosted.verify',
				params: {
					server: this.serverDoc
				},
				onSuccess(data) {
					if (data) {
						this.playOutput = true;
						this.unreachable = false
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
						document.getElementById('region-consent').focus();

						return 'Please agree to the above consent to create server';
					}
					if (!canCreate) {
						return 'Cannot create server';
					}
				}
			};
		}
	},
	computed: {},
	methods: {
		async nextStep(activeStep, next) {
			if (activeStep.name === 'ServerDetails') {
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
		async startVerification() {
			this.playStatus = true;
			await this.$resources.verify.submit();
			this.playStatus = false;
		},
		verifyIP(ip) {
			const ipAddressRegex = /^([0-9]{1,3}\.){3}[0-9]{1,3}$/;
			const ver = ipAddressRegex.test(ip);
			return ver;
		}
	}
};
</script>
