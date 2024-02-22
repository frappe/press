<template>
	<WizardCard>
		<div>
			<div class="mb-6 text-center">
				<h1 class="text-2xl font-bold sm:text-center">New Bench</h1>
				<p v-if="serverTitle" class="text-base text-gray-700">
					Bench will be created on server
					<span class="font-medium">{{ serverTitle.slice(0, -14) }}</span>
				</p>
			</div>
			<div v-if="$resources.options.loading" class="flex justify-center">
				<LoadingText />
			</div>
			<div class="space-y-8 sm:space-y-6" v-else>
				<div>
					<label class="text-lg font-semibold">
						Choose a name for your bench
					</label>
					<p class="text-base text-gray-700">
						Name your bench based on its purpose. For e.g., Personal Websites,
						Staging Bench, etc.
					</p>
					<FormControl class="mt-2" v-model="benchTitle" />
				</div>
				<div v-if="regionOptions.length > 0">
					<h2 class="text-lg font-semibold">Select Region</h2>
					<p class="text-base text-gray-700">
						Select the datacenter region where your bench should be created
					</p>
					<div class="mt-2">
						<RichSelect
							:value="selectedRegion"
							@change="selectedRegion = $event"
							:options="regionOptions"
						/>
					</div>
				</div>
				<div>
					<label class="text-lg font-semibold"> Select a Frappe version </label>
					<p class="text-base text-gray-700">
						Select a Frappe version for your bench.
					</p>
					<FormControl
						class="mt-2"
						type="select"
						v-model="selectedVersionName"
						:options="versionOptions"
					/>
				</div>

				<div v-if="selectedVersionName">
					<label class="text-lg font-semibold"> Select apps to install </label>
					<p class="text-base text-gray-700">
						These apps will be available for sites on your bench. You can also
						add apps to your bench later.
					</p>
					<div class="mt-4">
						<AppSourceSelector
							:apps="[
								...selectedVersion.apps.filter(app => app.name === 'frappe'),
								...selectedVersion.apps.filter(app => app.name !== 'frappe')
							]"
							v-model="selectedApps"
							:multiple="true"
						/>
					</div>
				</div>
				<!-- Region consent checkbox -->
				<div class="my-6">
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

				<div class="flex justify-between">
					<ErrorMessage class="mb-2" :message="$resources.createBench.error" />
					<Button
						variant="solid"
						class="ml-auto"
						:loading="$resources.createBench.loading"
						@click="$resources.createBench.submit()"
					>
						Create Bench
					</Button>
				</div>
			</div>
		</div>
	</WizardCard>
</template>

<script>
import WizardCard from '@/components/WizardCard.vue';
import AppSourceSelector from '@/components/AppSourceSelector.vue';
import RichSelect from '@/components/RichSelect.vue';
export default {
	name: 'NewBench',
	props: ['saas_app', 'server'],
	components: {
		WizardCard,
		AppSourceSelector,
		RichSelect
	},
	data() {
		return {
			benchTitle: null,
			selectedVersionName: null,
			selectedApps: [],
			selectedRegion: null,
			serverTitle: null,
			agreedToRegionConsent: false
		};
	},
	resources: {
		options() {
			return {
				url: 'press.api.bench.options',
				initialData: {
					versions: [],
					clusters: []
				},
				auto: true,
				onSuccess(options) {
					if (!this.selectedVersionName) {
						this.selectedVersionName = options.versions[0].name;
					}
					if (!this.selectedRegion) {
						this.selectedRegion = this.options.clusters[0].name;
					}
				}
			};
		},
		createBench() {
			return {
				url: 'press.api.bench.new',
				params: {
					bench: {
						title: this.benchTitle,
						version: this.selectedVersionName,
						cluster: this.selectedRegion,
						saas_app: this.saas_app || null,
						apps: this.selectedApps.map(app => ({
							name: app.app,
							source: app.source.name
						})),
						server: this.server || null
					}
				},
				validate() {
					if (!this.benchTitle) {
						return 'Bench Title cannot be blank';
					}
					if (!this.selectedVersionName) {
						return 'Select a version to create bench';
					}
					if (this.selectedApps.length < 1) {
						return 'Select atleast one app to create bench';
					}

					if (!this.agreedToRegionConsent) {
						document.getElementById('region-consent').focus();
						return 'Please agree to the above consent to create bench';
					}
				},
				onSuccess(benchName) {
					this.$router.push(`/benches/${benchName}`);
				}
			};
		}
	},
	async mounted() {
		if (this.server) {
			let { title, cluster } = await this.$call(
				'press.api.server.get_title_and_cluster',
				{
					name: this.server
				}
			);
			this.serverTitle = title;
			this.selectedRegion = cluster;
		}
	},
	watch: {
		selectedVersionName() {
			this.$nextTick(() => {
				let frappeApp = this.getFrappeApp(this.selectedVersion.apps);
				this.selectedApps = [{ app: frappeApp.name, source: frappeApp.source }];
			});
		},
		selectedApps: {
			handler(newVal, oldVal) {
				// dont remove frappe app
				let hasFrappe = newVal.find(app => app.app === 'frappe');
				if (!hasFrappe && oldVal) {
					this.selectedApps = oldVal;
				}
			},
			deep: true
		}
	},
	methods: {
		getFrappeApp(apps) {
			return apps.find(app => app.name === 'frappe');
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		selectedVersion() {
			return this.options.versions.find(
				v => v.name === this.selectedVersionName
			);
		},
		versionOptions() {
			return this.options.versions.map(v => ({
				label: `${v.name} (${v.status})`,
				value: v.name
			}));
		},
		regionOptions() {
			let clusters = this.options.clusters;
			if (this.server && this.selectedRegion) {
				clusters = clusters.filter(
					cluster => cluster.name === this.selectedRegion
				);
			}
			return clusters.map(d => ({
				label: d.title,
				value: d.name,
				image: d.image,
				beta: d.beta
			}));
		}
	}
};
</script>
