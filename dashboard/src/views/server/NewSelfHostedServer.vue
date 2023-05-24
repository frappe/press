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
				<Hostname
					:options="options"
					v-show="activeStep.name === 'Hostname'"
					v-model:title="title"
					v-model:selectedRegion="selectedRegion"
				/>
					<SelfHostedServerForm
					v-show="activeStep.name === 'ServerDetails'"
					v-model:publicIp="publicIP"
					v-model:privateIp="privateIP"
					/>
				<div class="mt-4">
				<SelfHostedServerVerify
					v-show="activeStep.name === 'VerifyServer'"
					v-model:ssh_key="ssh_key"/>
			<Button v-show="activeStep.name === 'VerifyServer'" :loading="playStatus" appearance="primary" @click="startVerification">Verify Server</Button>
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
			publicIP:null,
			privateIP:null,
			validationMessage: null,
			newDoc:null,
			playID:null,
			playStatus:false,
			playOutput:null,
			ssh_key:null,
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
						return this.privateIP && this.publicIP
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
		this.ssh_key = await this.$call("press.api.selfhosted.sshkey")
	},
	resources: {
		newServer() {
			return {
				method: 'press.api.selfhosted.new',
				params: {
					server: {
						title: this.title,
						cluster: this.selectedRegion,
						publicIP: this.publicIP,
						privateIP: this.privateIP,
					}
				},
				onSuccess(data) {
					this.newDoc = data
				},
				validate() {
					let canCreate = this.title


					// if (!this.agreedToRegionConsent) {
					// 	document.getElementById('region-consent').focus();
					//
					// 	return 'Please agree to the above consent to create server';
					// }

					if (!canCreate) {
						return 'Cannot create server';
					}
				}
			};
		},
		verify(){
			return{
				method: 'press.api.selfhosted.verify',
				params:{
					server:this.newDoc
				},
				onSuccess(data){
					this.playID = data
				}
			}
		}
	},
	computed: {},
	methods: {
		async nextStep(activeStep, next) {
			if (activeStep.name === 'ServerDetails'){
				console.log("Heyyo")
				this.$resources.newServer.submit()
			}
			next();
		},
		async startVerification(){
			this.playStatus=true
			await this.$resources.verify.submit()
			setTimeout(this.verifyStatus,10000)
		},
		async verifyStatus(){

			this.playOutput = this.$call("press.api.selfhosted.verify_status",{
				play:this.playID
			})


			if (!this.playOutput){
				for(let i=0;i<=3;i++){
					console.log("Onnude",i)
					this.playStatus=true
					setTimeout(this.verifyStatus,2000)
				}
			}

			this.playStatus = false
		}
	}
};
</script>
