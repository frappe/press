<template>
	<WizardCard v-if="options">
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Create a new server</h1>
		</div>
		<Steps :steps="steps">
			<template
				v-slot="{ active: activeStep, next, previous, hasPrevious, hasNext }"
			>
				<div class="mt-8"></div>
				<Hostname
					:options="options"
					v-show="activeStep.name === 'Hostname'"
					v-model:title="title"
					v-model:selectedRegion="selectedRegion"
				/>
					<SelfHostedServerForm
					v-show="activeStep.name === 'ServerDetails'"
					v-model:public_ip="public_ip"
					v-model:private_ip="private_ip"
					v-model:ssh_user="ssh_user"
					v-model:ssh_port="ssh_port"
					/>
				<SelfHostedServerVerify
					v-show="activeStep.name === 'VerifyServer'"
					v-model:ssh_key="ssh_key"/>
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
					<!-- <NewSelfHostedServerForm/> -->
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
							@click="$resources.newServer.submit()"
							:loading="$resources.newServer.loading"
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
import Hostname from './NewServerHostname.vue';
import SelfHostedServerForm from './NewSelfHostedServerForm.vue'
import SelfHostedServerVerify from './SelfHostedServerVerify.vue'
export default {
	name: 'NewSelfHostedServer',
	components: {
		WizardCard,
		Steps,
		Hostname,
		SelfHostedServerForm,
		SelfHostedServerVerify
	},
	data() {
		return {
			title: null,
			options: null,
			selectedRegion: null,
			public_ip:null,
			private_ip:null,
			ssh_user:null,
			ssh_port:null,
			validationMessage: null,
			ssh_key:"Ajsbadgiiuerzxtcfgvhbjnkmlztwerxdyctfvyghjnkmxyertcyvubindxtcfgv",
			steps: [
				{
					name: 'Hostname',
					validate: () => {
						return this.title && this.selectedRegion;
					}
				},
				{
					name:"ServerDetails",
					validate:()=>{
						return this.private_ip && this.public_ip && this.ssh_port && this.ssh_user
					}
				},
				{
					name: 'VerifyServer'
				}
			],
			agreedToRegionConsent: false
		};
	},
	async mounted() {
		this.options = await this.$call('press.api.server.options',{
				type: "self_hosted"
		});
	},
	resources: {
		newServer() {
			return {
				method: 'press.api.server.new',
				params: {
					server: {
						title: this.title,
						cluster: this.selectedRegion,
						app_plan: this.selectedAppPlan?.name,
						db_plan: this.selectedDBPlan?.name
					}
				},
				onSuccess(data) {
					let { server } = data;
					this.$router.push(`/servers/${server}/install`);
				},
				validate() {
					let canCreate = this.title


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
			next();
		}
	}
};
</script>
