<template>
	<div class="mt-5">
		<div class="px-8">
			<div
				class="p-8 mx-auto mb-20 space-y-8 border rounded-lg shadow-md"
				style="width: 650px"
			>
				<div>
					<h1 class="mb-6 text-2xl font-bold">Add a New App</h1>

					<div v-if="$resources.options.loading === true">
						<p class="text-base text-gray-700">
							Fetching your repositories.
						</p>
					</div>
					<div v-if="options.enable_custom_apps === true">
						<div
							v-if="
								options.authorized === false ||
									(options.authorized === true &&
										options.installations.length == 0)
							"
						>
							<label class="text-lg">
								Connect to GitHub
							</label>
							<p class="text-base text-gray-700">
								Connect to GitHub to access your repositories.
							</p>
							<Button class="mt-6" type="primary">
								<a :href="options.installation_url">Connect To GitHub</a>
							</Button>
						</div>
					</div>
					<div v-if="options.enable_custom_apps === false">
						<label class="text-lg">
							You are not authorized to use this feature. Contact support.
						</label>
					</div>
					<div v-if="options.authorized === true">
						<div v-if="options.installations.length != 0">
							<label class="text-lg">
								Choose a GitHub Repository
							</label>

							<p class="text-base text-gray-700">
								When you push to Git we will make magic happen.
							</p>
							<div class="mt-4">
								<Input
									type="select"
									v-model="selectedInstallationId"
									:options="installationOptions"
								/>
							</div>
							<div class="text-base text-gray-700 mt-4">
								Not this account?
								<a :href="options.installation_url" class="underline"
									>Add another organization.</a
								>
							</div>
							<div v-if="!connectedRepository">
								<div v-if="selectedInstallation.repos.length != 0" class="mt-4">
									<div
										v-for="repo in selectedInstallation.repos"
										:key="repo.id"
										class="text-base flex py-1"
									>
										<div :href="repo.url" class="flex-1">
											{{ selectedInstallation.login }} /
											<span class="font-semibold">{{ repo.name }}</span>
										</div>
										<Button
											class=" text-right"
											@click="connectedRepository = repo"
										>
											Connect
										</Button>
									</div>
									<p class="text-base text-gray-700 mt-4">
										Don't see your repository here?
										<a
											:href="
												`https://github.com/settings/installations/${selectedInstallation.id}?repository_ids=`
											"
											class="underline"
											>Configure the Frappe Cloud app on GitHub.</a
										>
									</p>
								</div>
								<div v-if="selectedInstallation.repos.length == 0" class="mt-4">
									<label class="text-lg text-red-600">
										No repositories found
									</label>
									<p class="text-base text-gray-700 mt-4">
										This can happen when Frappe Cloud doesn’t have access to the
										repositories in your account.
										<a
											:href="
												`https://github.com/settings/installations/${selectedInstallation.id}?repository_ids=`
											"
											class="underline"
											>Configure the Frappe Cloud app on GitHub</a
										>, and give it access to the repository you want to link.
									</p>
								</div>
							</div>
							<div v-if="connectedRepository">
								<div class="mt-4 flex">
									<div class="flex-1 text-lg">
										Connected To
										<a :href="connectedRepository.url" class="underline"
											>{{ selectedInstallation.login }} /
											<span class="font-semibold">{{
												connectedRepository.name
											}}</span></a
										>
									</div>
									<Button
										class="text-right"
										type="danger"
										@click="connectedRepository = null"
									>
										Disconnect
									</Button>
								</div>
								<div v-if="$resources.repository.loading === true" class="mt-4">
									<p class="text-base text-gray-700">
										Fetching repository from GitHub.
									</p>
								</div>
								<div v-if="$resources.repository.loading === false">
									<div class="mt-4">
										<label class="text-lg">
											Choose a branch to deploy
										</label>

										<p class="text-base text-gray-700">
											Every push to the branch you specify here will be
											available to deploy a new version of this app.
										</p>
										<div class="mt-4">
											<Input
												type="select"
												v-model="selectedBranch"
												:options="branchOptions"
											/>
										</div>
										<div class="mt-6">
											<div
												v-if="$resources.app.loading === true"
												class="text-base text-gray-700"
											>
												Scanning
												<a
													:href="
														connectedRepository.url + '/tree/' + selectedBranch
													"
													class="underline"
												>
													<span class="font-semibold">{{
														selectedBranch
													}}</span></a
												>
												branch for a Frappe application.
											</div>
											<div v-if="$resources.app.loading === false">
												<div v-if="scrubbed" class="text-lg flex">
													<FeatherIcon
														name="check"
														class="w-5 h-5 p-1 mr-2 text-green-500 bg-green-100 rounded-full"
													/>
													Found {{ scrubbed }}
												</div>
												<div v-if="!scrubbed" class="text-lg text-red-600 flex">
													<FeatherIcon
														name="x"
														class="w-5 h-5 p-1 mr-2 text-red-500 bg-red-100 rounded-full"
													/>
													Couldn't find a Frappe application.
												</div>
											</div>
										</div>
									</div>
									<div class="mt-6" v-if="scrubbed">
										<label class="text-lg">
											Choose a name for your app
										</label>
										<p class="text-base text-gray-700">
											Give your app a unique name.
										</p>
										<div class="flex mt-4">
											<input
												class="z-10 w-full form-input"
												type="text"
												v-model="appName"
												@change="checkIfExists()"
											/>
										</div>
										<ErrorMessage class="mt-1" :error="appNameInvalidMessage" />
									</div>
									<div class="mt-6" v-if="scrubbed">
										<label class="text-lg">
											Choose compatible Frappe versions
										</label>
										<p class="text-base text-gray-700">
											Your app will be available for installation with these
											versions.
										</p>
										<div class="flex pl-1 -ml-1 overflow-x-auto pb-2 pt-4">
											<button
												class="relative flex items-center justify-center py-4 pl-4 pr-8 mr-4 border rounded-md focus:outline-none focus:shadow-outline"
												:class="[
													selectedGroups.includes(group.name)
														? 'bg-blue-50 border-blue-500'
														: 'hover:border-blue-400',
													checkAvailability(group)
														? 'cursor-pointer'
														: 'cursor-not-allowed bg-gray-50 border-gray-500'
												]"
												v-for="group in options.groups"
												:key="group.name"
												@click="toggleVersion(group)"
												:disabled="!checkAvailability(group)"
											>
												<div class="flex items-start">
													<Input
														class="pt-0.5 pointer-events-none"
														tabindex="-1"
														type="checkbox"
														:value="selectedGroups.includes(group.name)"
													/>
													<div class="ml-3 text-base text-left">
														<div class="font-semibold">
															{{ group.name }}
														</div>
														<div class="text-gray-700">
															{{ group.frappe.scrubbed }}/{{
																group.frappe.branch
															}}
														</div>
													</div>
												</div>
											</button>
										</div>
									</div>
									<div class="mt-6" v-if="scrubbed">
										<label class="flex py-2 leading-none">
											<Input
												label="Enable Auto Deploy"
												type="checkbox"
												v-model="enableAutoDeploy"
											/>
										</label>
										<p class="text-base text-gray-700">
											Deploys happen automatically: be sure that this branch is
											always in a deployable state and any tests have passed
											before you push.
										</p>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div v-if="scrubbed">
						<Button
							class="mt-6"
							type="primary"
							@click="createApp()"
							:disabled="!canCreate()"
						>
							Create App
						</Button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'NewApp',
	data() {
		return {
			selectedInstallationId: null,
			connectedRepository: null,
			enableAutoDeploy: false,
			selectedBranch: null,
			selectedGroups: [],
			scrubbed: null,
			appName: null,
			appNameTaken: false,
			appNameInvalidMessage: null
		};
	},
	methods: {
		async createApp() {
			let appName = await this.$call('press.api.app.new', {
				app: {
					name: this.appName,
					installation: this.selectedInstallation.id,
					url: this.connectedRepository.url,
					repo_owner: this.selectedInstallation.login,
					repo: this.connectedRepository.name,
					branch: this.selectedBranch,
					scrubbed: this.scrubbed,
					enable_auto_deploy: this.enableAutoDeploy,
					groups: this.selectedGroups
				}
			});
			this.$router.push(`/apps/${appName}`);
		},
		toggleVersion(group) {
			if (!this.selectedGroups.includes(group.name)) {
				this.selectedGroups.push(group.name);
			} else {
				this.selectedGroups = this.selectedGroups.filter(a => a !== group.name);
			}
		},
		checkAvailability(group) {
			let matched = group.apps.find(a => a.scrubbed === this.scrubbed);
			return !matched;
		},
		async checkIfExists() {
			this.appNameTaken = await this.$call('press.api.app.exists', {
				name: this.appName
			});
			if (this.appNameTaken) {
				this.appNameInvalidMessage = `${this.appName} already exists`;
			}
		},
		canCreate() {
			if (
				this.appName &&
				!this.appNameInvalidMessage &&
				this.selectedGroups.length != 0
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
		connectedRepository() {
			this.selectedBranch = null;
			this.scrubbed = null;
			if (this.connectedRepository) {
				this.$resources.repository.reload();
			}
		},
		selectedBranch() {
			this.scrubbed = null;
			if (this.selectedBranch) {
				this.$resources.app.reload();
			}
		},
		scrubbed() {
			this.selectedGroups = [];
			let available = this.options.groups.find(
				g => this.checkAvailability(g) === true
			);
			if (available) {
				this.selectedGroups.push(available.name);
			}
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		repository() {
			return this.$resources.repository.data;
		},
		installationOptions() {
			return this.options.installations.map(installation => ({
				label: installation.login,
				value: installation.id
			}));
		},
		branchOptions() {
			return this.repository.branches.map(i => i.name);
		},
		selectedInstallation() {
			return this.options.installations.find(
				i => i.id == this.selectedInstallationId
			);
		},
		repositoryParams() {
			if (this.selectedInstallation && this.connectedRepository) {
				return {
					installation: this.selectedInstallation.id,
					owner: this.selectedInstallation.login,
					name: this.connectedRepository.name
				};
			}
			return {};
		},
		appParams() {
			if (this.selectedInstallation && this.connectedRepository) {
				return {
					installation: this.selectedInstallation.id,
					owner: this.selectedInstallation.login,
					repository: this.connectedRepository.name,
					branch: this.selectedBranch
				};
			}
			return {};
		}
	},
	resources: {
		options() {
			return {
				method: 'press.api.github.options',
				default: {
					installations: []
				},
				auto: true,
				onSuccess(options) {
					this.selectedInstallationId = options.installations[0].id;
				}
			};
		},
		repository() {
			return {
				method: 'press.api.github.repository',
				params: this.repositoryParams,
				default: {
					branches: []
				},
				onSuccess(repository) {
					this.selectedBranch = repository.default_branch;
				},
				auto: false
			};
		},
		app() {
			return {
				method: 'press.api.github.app',
				params: this.appParams,
				default: {},
				onSuccess(app) {
					this.scrubbed = app.name;
					this.appName = app.title;
					this.checkIfExists();
				},
				auto: false
			};
		}
	}
};
</script>
