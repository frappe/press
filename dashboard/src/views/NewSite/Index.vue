<template>
	<div class="mt-5">
		<div class="px-8" v-if="options">
			<div
				class="p-8 mx-auto mb-20 space-y-8 border rounded-lg shadow-md"
				style="width: 650px"
			>
				<h1 class="mb-6 text-2xl font-bold text-center">Create a New Site</h1>
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
						/>
						<Restore
							:options="options"
							:selectedFiles.sync="selectedFiles"
							v-show="activeStep.name == 'Restore'"
						/>
						<Plans
							:selectedPlan.sync="selectedPlan"
							:options="options"
							v-show="activeStep.name === 'Plan'"
						/>
						<div class="mt-4">
							<ErrorMessage :error="$resources.newSite.error" />
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
									@click="next"
									:class="{
										'opacity-0 pointer-events-none': !hasNext
									}"
								>
									Next
								</Button>
								<Button
									v-show="!wantsToRestore && activeStep.name === 'Restore'"
									type="primary"
									@click="next"
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
			</div>
		</div>
	</div>
</template>

<script>
import Steps from '@/components/Steps';
import Hostname from './Hostname';
import Apps from './Apps';
import Restore from './Restore';
import Plans from './Plans';

export default {
	name: 'NewSite',
	components: {
		Steps,
		Hostname,
		Apps,
		Restore,
		Plans
	},
	data() {
		return {
			subdomain: null,
			subdomainValid: false,
			options: null,
			privateBench: false,
			selectedApps: [],
			selectedGroup: null,
			selectedFiles: {
				database: null,
				public: null,
				private: null
			},
			selectedPlan: null,
			steps: [
				{
					name: 'Hostname',
					validate: () => {
						return this.subdomainValid;
					}
				},
				{
					name: 'Apps'
				},
				{
					name: 'Restore'
				},
				{
					name: 'Plan'
				}
			]
		};
	},
	async mounted() {
		this.options = await this.$call('press.api.site.options_for_new');
		this.options.plans = this.options.plans.map(plan => {
			plan.disabled = this.disablePlan(plan);
			return plan;
		});

		if (this.$route.query.domain) {
			let domain = this.$route.query.domain.split('.');
			if (domain) {
				this.subdomain = domain[0];
			}
			this.$router.replace({});
		}
		if (this.$route.query.bench) {
			this.privateBench = true;
			this.selectedGroup = this.$route.query.bench;
			this.$router.replace({});
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
						plan: this.selectedPlan ? this.selectedPlan.name : null,
						files: this.selectedFiles
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

					if (!canCreate) {
						return 'Cannot create site';
					}
				}
			};
		}
	},
	methods: {
		canCreateSite() {},
		disablePlan(plan) {
			if (this.options.free_account) {
				return false;
			}
			if (this.options.allow_partner) {
				return false;
			}
			if (this.options.has_card) {
				return false;
			}
			if (this.options.disable_site_creation) {
				return true;
			}
			if (plan.trial_period) {
				return false;
			}
			return true;
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
	}
};
</script>
