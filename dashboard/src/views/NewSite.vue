<template>
	<WizardCard v-if="options">
		<div class="mb-6 text-center ">
			<h1 class="text-2xl font-bold">
				Create a new site
			</h1>
			<p v-if="benchTitle" class="text-base text-gray-700">
				Site will be created on bench
				<span class="font-medium">{{ benchTitle }}</span>
			</p>
		</div>
		<Steps :steps="steps">
			<template
				v-slot="{
					active: activeStep,
					next,
					previous,
					hasPrevious,
					hasNext
				}"
			>
				<div class="mt-8"></div>
				<Hostname
					:options="options"
					v-show="activeStep.name === 'Hostname'"
					v-model="subdomain"
					@error="error => (subdomainValid = !Boolean(error))"
				/>
				<Apps
					:options="options"
					v-show="activeStep.name === 'Apps'"
					:privateBench="privateBench"
					:selectedApps.sync="selectedApps"
					:selectedGroup.sync="selectedGroup"
					:selectedRegion.sync="selectedRegion"
					:shareDetailsConsent.sync="shareDetailsConsent"
				/>

				<div class="mb-9" v-show="activeStep.name === 'Select App Plans'">
					<ChangeAppPlanSelector v-for="app in Object.keys(selectedAppPlans)" :key="app" :app="app" />
				</div>

				<Restore
					:options="options"
					:selectedFiles.sync="selectedFiles"
					:skipFailingPatches.sync="skipFailingPatches"
					v-show="activeStep.name == 'Restore'"
				/>
				<Plans
					:selectedPlan.sync="selectedPlan"
					:options="options"
					v-show="activeStep.name === 'Plan'"
				/>
				<ErrorMessage :error="validationMessage" />
				<div class="mt-4">
					<!-- Region consent checkbox -->
					<div class="my-6" v-if="!hasNext">
						<input
							id="region-consent"
							type="checkbox"
							class="
								h-4
								w-4
								text-blue-600
								focus:ring-blue-500
								border-gray-300
								rounded
							"
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

					<ErrorMessage class="mb-4" :error="$resources.newSite.error" />

					<div class="flex justify-between">
						<Button
							@click="previous"
							:class="{
								'opacity-0 pointer-events-none': !hasPrevious
							}"
						>
							Back
						</Button>
						<Button
							v-show="activeStep.name !== 'Restore' || wantsToRestore"
							type="primary"
							@click="nextStep(activeStep, next)"
							:class="{
								'opacity-0 pointer-events-none': !hasNext
							}"
						>
							Next
						</Button>
						<Button
							v-show="!wantsToRestore && activeStep.name === 'Restore'"
							type="primary"
							@click="nextStep(activeStep, next)"
						>
							Skip
						</Button>
						<Button
							v-show="!hasNext"
							type="primary"
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
import { DateTime } from 'luxon';
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
			options: null,
			privateBench: false,
			benchTitle: null,
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
						// if (!this.selectedRegion) {
						// 	this.validationMessage = 'Please select the region';
						// 	return false;
						// } else {
						// 	this.validationMessage = null;
						// }
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
			selectedAppPlans: {}
		};
	},
	async mounted() {
		this.options = await this.$call('press.api.site.options_for_new');
		this.options.plans = this.options.plans.map(plan => {
			plan.disabled = !this.$account.hasBillingInfo;
			return plan;
		});
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
			let { title, creation } = await this.$call('frappe.client.get_value', {
				doctype: 'Release Group',
				name: this.bench,
				fieldname: JSON.stringify(['title', 'creation'])
			});
			this.benchTitle = title;

			// poor man's bench paywall
			// this will disable creation of $10 sites on private benches
			// wanted to avoid adding a new field, so doing this with a date check :)
			let benchCreation = DateTime.fromSQL(creation);
			let paywalledBenchDate = DateTime.fromSQL('2021-09-21 00:00:00');
			let isPaywalledBench = benchCreation > paywalledBenchDate;
			if (isPaywalledBench && $account.user.user_type != 'System User') {
				this.options.plans = this.options.plans.filter(
					plan => plan.price_usd >= 25
				);
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
						skip_failing_patches: this.skipFailingPatches
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
						(!this.wantsToRestore ||
							Object.values(this.selectedFiles).every(v => v));

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
			let {
				database,
				public: publicFile,
				private: privateFile
			} = this.selectedFiles;
			if (!(database && publicFile && privateFile)) {
				return false;
			}
			return true;
		}
	},
	methods: {
		async nextStep(activeStep, next) {
			if (activeStep.name == "Apps") {
				console.log("apps selected.");
				// Go fetch app plans if any
				this.appsWithPlans = await this.$call('press.api.marketplace.get_apps_with_plans', {
					apps: JSON.stringify(this.selectedApps)
				});

				if (this.appsWithPlans && this.appsWithPlans.length > 0) {
					this.addPlanSelectionStep();

					for (let app of this.appsWithPlans) {
						this.selectedAppPlans[app] = null;
					}
				}
			}

			next();
		},
		addPlanSelectionStep() {
			const appsStepIndex = this.steps.findIndex(step => step.name == 'Apps');

			this.steps.splice(appsStepIndex + 1, 0, {
				name: `Select App Plans`
			});
		}
	}
};
</script>
