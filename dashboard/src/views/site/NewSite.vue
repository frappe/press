<template>
	<WizardCard>
		<div class="mb-6 text-center">
			<h1 class="text-2xl font-bold">Create a new site</h1>
			<p v-if="benchTitle" class="text-base text-gray-700">
				Site will be created on bench
				<span class="font-medium">{{ benchTitle }}</span>
			</p>
		</div>
		<Steps :steps="steps">
			<template
				v-slot="{ active: activeStep, next, previous, hasPrevious, hasNext }"
			>
				<div class="mt-8"></div>
				<Hostname
					v-show="activeStep.name === 'Hostname'"
					v-model="subdomain"
					@error="error => (subdomainValid = !Boolean(error))"
				/>
				<Apps
					v-show="activeStep.name === 'Apps'"
					:privateBench="privateBench"
					:bench="benchName"
					v-model:selectedApps="selectedApps"
					v-model:selectedGroup="selectedGroup"
					v-model:selectedRegion="selectedRegion"
					v-model:shareDetailsConsent="shareDetailsConsent"
				/>

				<div v-if="activeStep.name === 'Select App Plans'">
					<ChangeAppPlanSelector
						v-for="app in appsWithPlans"
						:key="app.name"
						:app="app.name"
						:group="selectedGroup"
						:editable="false"
						class="mb-9"
						@change="plan => (selectedAppPlans[app.name] = plan.name)"
					/>
				</div>

				<Restore
					v-model:selectedFiles="selectedFiles"
					v-model:skipFailingPatches="skipFailingPatches"
					v-show="activeStep.name == 'Restore'"
				/>
				<Plans
					v-model:selectedPlan="selectedPlan"
					:bench="bench"
					:benchTeam="benchTeam"
					v-show="activeStep.name === 'Plan'"
				/>
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

					<ErrorMessage class="mb-4" :message="$resources.newSite.error" />

					<div class="flex justify-between">
						<Button v-show="hasPrevious" @click="previous"> Back </Button>
						<Button
							v-show="
								(activeStep.name !== 'Restore' || wantsToRestore) && hasNext
							"
							class="ml-auto"
							variant="solid"
							@click="nextStep(activeStep, next)"
							:class="{ 'mt-2': hasPrevious }"
							:loading="loadingPlans"
							loadingText="Loading"
						>
							Next
						</Button>
						<Button
							v-show="
								!wantsToRestore && activeStep.name === 'Restore' && hasNext
							"
							class="ml-auto"
							variant="solid"
							@click="nextStep(activeStep, next)"
						>
							Skip
						</Button>
						<Button
							v-show="!hasNext"
							class="ml-auto"
							variant="solid"
							:class="{ 'mt-2': hasPrevious }"
							@click="$resources.newSite.submit()"
							:loading="$resources.newSite.loading"
						>
							Create Site
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
import Hostname from './NewSiteHostname.vue';
import Apps from './NewSiteApps.vue';
import Restore from './NewSiteRestore.vue';
import Plans from './NewSitePlans.vue';
import ChangeAppPlanSelector from '@/components/ChangeAppPlanSelector.vue';

export default {
	name: 'NewSite',
	props: ['bench'],
	components: {
		WizardCard,
		Steps,
		Hostname,
		Apps,
		Restore,
		Plans,
		ChangeAppPlanSelector
	},
	data() {
		return {
			subdomain: null,
			subdomainValid: false,
			privateBench: false,
			benchName: null,
			benchTitle: null,
			benchTeam: null,
			selectedApps: [],
			selectedGroup: null,
			selectedRegion: null,
			selectedFiles: {
				database: null,
				public: null,
				private: null
			},
			skipFailingPatches: false,
			selectedPlan: null,
			shareDetailsConsent: false,
			validationMessage: null,
			steps: [
				{
					name: 'Hostname',
					validate: () => {
						return this.subdomainValid;
					}
				},
				{
					name: 'Apps',
					validate: () => {
						if (this.privateBench) return true;
						if (!this.selectedRegion) {
							this.validationMessage = 'Please select the region';
							return false;
						} else {
							this.validationMessage = null;
						}
						return true;
					}
				},
				{
					name: 'Restore'
				},
				{
					name: 'Plan'
				}
			],
			agreedToRegionConsent: false,
			selectedAppPlans: {},
			loadingPlans: false
		};
	},
	async mounted() {
		if (this.$route.query.domain) {
			let domain = this.$route.query.domain.split('.');
			if (domain) {
				this.subdomain = domain[0];
			}
			this.$router.replace({});
		}
		if (this.bench) {
			this.privateBench = true;
			this.selectedGroup = this.bench;
			this.benchTitle = this.bench;
			let { title, creation, team } = await this.$call(
				'press.api.bench.get_title_and_creation',
				{
					name: this.bench
				}
			);
			this.benchName = this.bench;
			this.benchTitle = title;
			this.benchTeam = team;
			if (team == this.$account.team.name) {
				// Select a zero cost plan and remove the plan selection step
				this.selectedPlan = { name: 'Unlimited' };
				let plan_step_index = this.steps.findIndex(step => step.name == 'Plan');
				this.steps.splice(plan_step_index, 1);
			}
		}
	},
	resources: {
		newSite() {
			return {
				method: 'press.api.site.new',
				params: {
					site: {
						name: this.subdomain,
						apps: this.selectedApps,
						group: this.selectedGroup,
						cluster: this.selectedRegion,
						plan: this.selectedPlan ? this.selectedPlan.name : null,
						files: this.selectedFiles,
						share_details_consent: this.shareDetailsConsent,
						skip_failing_patches: this.skipFailingPatches,
						selected_app_plans: this.selectedAppPlans
					}
				},
				onSuccess(data) {
					let { site, job = '' } = data;
					this.$router.push(`/sites/${site}/jobs/${job}`);
				},
				validate() {
					let canCreate =
						this.subdomainValid &&
						this.selectedApps.length > 0 &&
						this.selectedPlan &&
						(!this.wantsToRestore || this.selectedFiles.database);

					if (!this.agreedToRegionConsent) {
						document.getElementById('region-consent').focus();

						return 'Please agree to the above consent to create site';
					}

					if (!canCreate) {
						return 'Cannot create site';
					}
				}
			};
		}
	},
	computed: {
		wantsToRestore() {
			if (this.selectedFiles.database) {
				return true;
			}
			return false;
		}
	},
	methods: {
		async nextStep(activeStep, next) {
			if (activeStep.name == 'Apps') {
				this.loadingPlans = true;

				// Fetch apps that have plans
				this.appsWithPlans = await this.$call(
					'press.api.marketplace.get_apps_with_plans',
					{
						apps: JSON.stringify(this.selectedApps),
						release_group: this.selectedGroup
					}
				);

				if (this.appsWithPlans && this.appsWithPlans.length > 0) {
					this.addPlanSelectionStep();

					this.selectedAppPlans = {};
					for (let app of this.appsWithPlans) {
						this.selectedAppPlans[app.name] = null;
					}
				} else {
					this.validationMessage = null;
					this.removePlanSelectionStepIfExists();
				}

				this.loadingPlans = false;
			}

			next();
		},
		addPlanSelectionStep() {
			const appsStepIndex = this.steps.findIndex(step => step.name == 'Apps');

			const selectAppPlansStepIndex = this.steps.findIndex(
				step => step.name == 'Select App Plans'
			);
			if (selectAppPlansStepIndex < 0) {
				this.steps.splice(appsStepIndex + 1, 0, {
					name: 'Select App Plans',
					validate: () => {
						for (let app of Object.keys(this.selectedAppPlans)) {
							if (!this.selectedAppPlans[app]) {
								this.validationMessage = `Please select a plan for ${app}`;
								return false;
							} else {
								this.validationMessage = null;
							}
						}

						return true;
					}
				});
			}
		},
		removePlanSelectionStepIfExists() {
			const selectAppPlansStepIndex = this.steps.findIndex(
				step => step.name == 'Select App Plans'
			);
			if (selectAppPlansStepIndex >= 0) {
				this.steps.splice(selectAppPlansStepIndex, 1);
			}
		}
	}
};
</script>
