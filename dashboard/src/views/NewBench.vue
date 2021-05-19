<template>
	<WizardCard>
		<div>
			<h1 class="mb-6 text-2xl font-bold sm:text-center">New Bench</h1>
			<div v-if="$resources.options.loading" class="flex justify-center">
				<Loading />
			</div>
			<div class="space-y-8 sm:space-y-6" v-else>
				<div>
					<label class="text-lg font-semibold">
						Choose a name for your bench
					</label>
					<p class="text-base text-gray-700">
						Name your bench based on it's purpose. For e.g., Personal Websites,
						Staging Bench, etc.
					</p>
					<Input class="mt-4" type="text" v-model="benchTitle" />
				</div>
				<div>
					<label class="text-lg font-semibold">
						Select a Frappe version
					</label>
					<p class="text-base text-gray-700">
						Select a Frappe version for your bench.
					</p>
					<Input
						class="mt-4"
						type="select"
						v-model="selectedVersionName"
						:options="versionOptions"
					/>
				</div>

				<div v-if="selectedVersionName">
					<label class="text-lg font-semibold">
						Select apps to install
					</label>
					<p class="text-base text-gray-700">
						These apps will be available for sites on your bench. You can also
						add apps to your bench later.
					</p>
					<div class="mt-4 space-y-3">
						<button
							class="block w-full px-4 py-3 text-left border rounded-md shadow cursor-pointer focus:outline-none focus:ring-2"
							:class="
								isAppSelected(app.name)
									? 'ring-2 ring-blue-500 bg-blue-50'
									: 'hover:border-blue-300 cursor-pointer'
							"
							v-for="app in selectedVersion.apps"
							:key="app.name"
							@click="toggleApp(app.name)"
						>
							<div
								class="flex items-center justify-between ml-1 text-base text-left"
							>
								<div>
									<div class="font-semibold">
										{{ app.title }}
									</div>
									<div class="text-gray-700">
										{{ app.source.repository_owner }}/{{
											app.source.repository
										}}
									</div>
								</div>
								<Dropdown :items="dropdownItems(app)" right>
									<template v-slot="{ toggleDropdown }">
										<Button
											type="white"
											@click.stop="toggleDropdown()"
											icon-right="chevron-down"
										>
											<span>{{ app.source.branch }}</span>
										</Button>
									</template>
								</Dropdown>
							</div>
						</button>
					</div>
				</div>
				<div>
					<ErrorMessage class="mb-2" :error="$resources.createBench.error" />
					<Button
						type="primary"
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
export default {
	components: { WizardCard },
	name: 'NewBench',
	data() {
		return {
			benchTitle: null,
			selectedVersionName: null,
			selectedApps: []
		};
	},
	resources: {
		options() {
			return {
				method: 'press.api.bench.options',
				default: {
					versions: []
				},
				auto: true,
				onSuccess(options) {
					if (!this.selectedVersionName) {
						this.selectedVersionName = options.versions[0].name;
					}
				}
			};
		},
		createBench() {
			return {
				method: 'press.api.bench.new',
				params: {
					bench: {
						title: this.benchTitle,
						version: this.selectedVersionName,
						apps: this.selectedApps
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
				},
				onSuccess(benchName) {
					this.$router.push(`/benches/${benchName}`);
				}
			};
		}
	},
	methods: {
		dropdownItems(app) {
			return app.sources.map(source => ({
				label: `${source.repository_owner}/${source.repository}:${source.branch}`,
				action: () => this.selectSource(app, source)
			}));
		},
		selectSource(app, source) {
			app.source = source;
			if (!this.isAppSelected(app.name)) {
				this.toggleApp(app.name);
			}
		},
		isAppSelected(name) {
			return Boolean(this.selectedApps.find(app => app.name == name));
		},
		toggleApp(name) {
			let selectedApps = this.selectedVersion.apps.filter(app => {
				if (app.name == 'frappe') {
					return true;
				} else if (app.name == name) {
					return !this.isAppSelected(app.name);
				}
				return this.isAppSelected(app.name);
			});
			this.selectedApps = selectedApps.map(app => ({
				name: app.name,
				source: app.source.name
			}));
		}
	},
	watch: {
		selectedVersionName() {
			this.selectedApps = [];
			this.toggleApp('frappe');
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
		}
	}
};
</script>
