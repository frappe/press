<template>
	<WizardCard v-if="domain">
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Create a new codespace</h1>
		</div>
		<Steps :steps="steps">
			<template
				v-slot="{ active: activeStep, next, previous, hasPrevious, hasNext }"
			>
				<div class="mt-8"></div>
				<Hostname
					v-show="activeStep.name === 'Hostname'"
					v-model="subdomain"
					:domain="domain"
					@error="error => (subdomainValid = !Boolean(error))"
				/>
				<Group v-show="activeStep.name === 'Group'" v-model="selectedGroup" />
				<Bench
					v-if="selectedGroup"
					v-show="activeStep.name === 'Bench'"
					v-model="selectedBench"
					:selectedGroup="selectedGroup.name"
				/>
				<div class="mt-4">
					<ErrorMessage
						class="mb-4"
						:message="$resources.newCodeServer.error"
					/>
					<div>
						<Button v-if="hasPrevious" class="w-full" @click="previous">
							Back
						</Button>
						<Button
							v-if="hasNext"
							class="w-full"
							variant="solid"
							@click="nextStep(activeStep, next)"
							:class="{ 'mt-2': hasPrevious }"
						>
							Next
						</Button>
						<Button
							v-show="!hasNext"
							class="w-full mt-2"
							variant="solid"
							@click="$resources.newCodeServer.submit()"
							:loading="$resources.newCodeServer.loading"
							:disabled="selectedBench == null"
						>
							Create Codespace
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
import Hostname from './NewCodeServerHostname.vue';
import Group from './NewCodeServerGroup.vue';
import Bench from './NewCodeServerBench.vue';

export default {
	name: 'NewServer',
	components: {
		WizardCard,
		Steps,
		Hostname,
		Group,
		Bench
	},
	data() {
		return {
			title: null,
			subdomain: null,
			domain: null,
			subdomainValid: false,
			selectedGroup: null,
			selectedBench: null,
			steps: [
				{
					name: 'Hostname',
					validate: () => {
						return this.subdomainValid;
					}
				},
				{
					name: 'Group',
					validate: () => {
						return this.selectedGroup != null;
					}
				},
				{
					name: 'Bench'
				}
			]
		};
	},
	async mounted() {
		this.domain = await this.$call('press.api.spaces.code_server_domain');
	},
	resources: {
		newCodeServer() {
			return {
				url: 'press.api.spaces.create_code_server',
				params: {
					subdomain: this.subdomain,
					bench: this.selectedBench,
					domain: this.domain
				},
				onSuccess(r) {
					this.$router.replace(`/codeservers/${r}/jobs`);
				},
				validate() {
					if (this.selectedBench === null) {
						return 'Please select a bench version to deploy the code server on';
					}
				}
			};
		}
	},
	methods: {
		async nextStep(activeStep, next) {
			next();
		}
	}
};
</script>
