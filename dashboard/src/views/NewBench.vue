<template>
	<div class="mt-5">
		<div class="px-8">
			<div
				class="p-8 mx-auto mb-20 space-y-8 border rounded-lg shadow-md"
				style="width: 700px"
			>
				<div>
					<h1 class="mb-6 text-2xl font-bold">New Bench</h1>
					<div v-if="$resources.options.loading === false">
						<div class="mt-4">
							<label class="text-lg">
								Choose a Frappe version
							</label>
							<p class="text-base text-gray-700">
								Select the Frappe version for your bench.
							</p>
							<div class="mt-4">
								<Input
									type="select"
									v-model="selectedVersionName"
									:options="versionOptions"
								/>
							</div>
						</div>
						<div class="mt-6">
							<label class="text-lg">
								Choose a name for your bench
							</label>
							<p class="text-base text-gray-700">
								Give your bench a unique name.
							</p>
							<div class="flex mt-4">
								<input
									class="z-10 w-full form-input"
									type="text"
									v-model="benchTitle"
								/>
							</div>
							<ErrorMessage class="mt-1" :error="benchTitleInvalidMessage" />
						</div>
						<div class="mt-6" v-if="selectedVersionName">
							<label class="text-lg">
								Choose apps to Install on your Bench
							</label>
							<p class="text-base text-gray-700">
								These apps will be available for sites on your bench. You can
								also add apps to your bench later.
							</p>
							<div class="grid grid-cols-2 gap-4 px-2 py-2 mt-2 -mx-2 max-h-56">
								<button
									class="px-4 py-3 text-left border border-blue-100 rounded-md focus:outline-none focus:shadow-none shadow cursor-pointer"
									:class="
										isAppSelected(app.name)
											? 'shadow-outline-blue border-blue-500'
											: 'hover:border-blue-300 cursor-pointer'
									"
									v-for="app in selectedVersion.apps"
									:key="app.name"
									@click="toggleApp(app.name)"
								>
									<div class="flex items-start">
										<div class="ml-1 text-base text-left">
											<div class="font-semibold">
												{{ app.title }}
											</div>
											<div>
												<Dropdown :items="dropdownItems(app)">
													<template v-slot="{ toggleDropdown }">
														<button
															class="flex items-center text-base focus:outline-none focus:shadow-none"
															id="user-menu"
															@click.stop="toggleDropdown()"
														>
															<div class="text-gray-700">
																<span>{{ app.source.repository_owner }}</span
																>:<span>{{ app.source.branch }}</span>
															</div>
															<FeatherIcon
																:name="'chevron-down'"
																class="w-4 h-4 ml-1 mt-0.5"
															/>
														</button>
													</template>
												</Dropdown>
											</div>
										</div>
									</div>
								</button>
							</div>
						</div>
					</div>
					<div v-if="benchTitle" class="mt-6">
						<ErrorMessage class="mb-2" :error="benchCreationErrorMessage" />
						<Button
							type="primary"
							@click="createBench()"
							:disabled="!canCreate()"
						>
							Create Bench
						</Button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'NewBench',
	data() {
		return {
			selectedVersionName: null,
			selectedVersion: null,
			selectedApps: [],
			benchTitle: null,
			benchTitleInvalidMessage: null,
			benchCreationErrorMessage: null
		};
	},
	methods: {
		async createBench() {
			let benchName = this.$call('press.api.bench.new', {
				bench: {
					title: this.benchTitle,
					version: this.selectedVersionName,
					apps: this.selectedApps
				}
			});
			benchName
				.then(response => {
					this.$router.push(`/benches/${response}`);
				})
				.catch(error => {
					this.benchCreationErrorMessage = error.messages[0];
				});
		},
		dropdownItems(app) {
			return app.sources.map(source => ({
				label: `${source.repository_owner}:${source.branch}`,
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
		},
		async checkIfTitleExists() {
			let benchTitleTaken = await this.$call('press.api.bench.exists', {
				title: this.benchTitle
			});
			if (benchTitleTaken) {
				this.benchTitleInvalidMessage = `${this.benchTitle} already exists`;
			} else {
				this.benchTitleInvalidMessage = null;
			}
		},
		canCreate() {
			if (
				this.benchTitle &&
				!this.benchTitleInvalidMessage &&
				!this.benchCreationErrorMessage &&
				this.selectedVersionName &&
				this.selectedApps.length != 0
			) {
				return true;
			}
			return false;
		}
	},
	errorCaptured(err, vm, info) {
		this.error = `${err.stack}\n\nfound in ${info} of component`;
		return false;
	},
	watch: {
		async selectedVersionName() {
			this.benchTitle = this.selectedVersionName;
			this.selectedVersion = this.options.versions.find(
				v => v.name === this.selectedVersionName
			);
			this.selectedApps = [];
			this.toggleApp('frappe');
		},
		async benchTitle() {
			this.checkIfTitleExists();
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		versionOptions() {
			return this.options.versions.map(v => v.name);
		}
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
		}
	}
};
</script>
