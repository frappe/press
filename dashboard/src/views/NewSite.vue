<template>
	<div>
		<PageHeader>
			<h1 slot="title">New Site</h1>
		</PageHeader>
		<div class="px-8" v-if="options">
			<div class="mb-5 border-t"></div>
			<div
				class="px-6 py-8 mx-auto mb-20 border border-gray-100 rounded-lg shadow-md"
				style="width: 650px"
			>
				<div>
					<label>
						Choose a hostname
					</label>
					<p class="text-sm text-gray-600">
						Give your site a unique name. It can only contain alphanumeric
						characters and dashes.
					</p>
					<div class="flex mt-6">
						<input
							class="z-10 w-full rounded-r-none form-input focus:bg-white"
							type="text"
							v-model="siteName"
							@change="checkIfValid"
							placeholder="subdomain"
							ref="siteName"
						/>
						<div class="flex items-center px-4 bg-gray-200 border rounded-r">
							.{{ options.domain }}
						</div>
					</div>
					<div class="mt-1 text-sm text-red-600" v-if="siteErrorMessage">
						{{ siteErrorMessage }}
					</div>
				</div>
				<div class="mt-10">
					<label>
						Choose your apps
					</label>
					<p class="text-sm text-gray-600">
						Select apps to install to your site. You can also choose a specific
						version of the app.
					</p>
					<div class="mt-6">
						<select class="form-select" v-model="selectedGroup">
							<option v-for="group in options.groups" :key="group.name">
								{{ group.name }}
							</option>
						</select>
					</div>
					<div class="mt-6">
						<div class="flex py-2 pl-1 -my-2 -ml-1 overflow-x-auto">
							<button
								class="flex items-center justify-center w-40 px-6 py-8 mr-4 border rounded cursor-pointer focus:outline-none focus:shadow-outline"
								:class="
									selectedApps.includes(app.app)
										? 'bg-blue-100 border-blue-500'
										: 'hover:bg-gray-100'
								"
								v-for="app in apps"
								:key="app.app"
								@click="toggleApp(app)"
							>
								<div>
									<img
										class="w-8 h-8 mx-auto"
										:src="app.logo"
										:alt="app.name"
									/>
									<div class="mt-3 font-semibold">
										{{ app.repo }}
									</div>
								</div>
							</button>
						</div>
					</div>
				</div>
				<div class="mt-10">
					<label class="flex py-2 leading-none">
						<input
							type="checkbox"
							class="form-checkbox"
							v-model="restoreBackup"
						/>
						<span class="ml-2">
							Create Site from Backup
						</span>
					</label>
					<p class="text-sm text-gray-600">
						Upload backup files instead of starting from a blank site.
					</p>
					<div v-if="restoreBackup" class="pl-2">
						<div v-for="file in files" :key="file.type">
							<div class="flex items-center mt-1">
								<span class="flex-1 text-gray-800">{{ file.title }}</span>
								<span
									class="flex-1 text-gray-400 truncate text-sm"
									v-if="file.file"
								>
									{{ file.file.name }}
								</span>
								<span
									class="flex-1 text-red-400 text-sm"
									v-if="file.errorMessage"
								>
									{{ file.errorMessage }}
								</span>
								<input
									:ref="file.type"
									type="file"
									class="hidden"
									@change="onFile(file, $event)"
								/>
								<Button
									class="ml-4 flex-2"
									:disabled="file.uploading"
									@click="$refs[file.type][0].click()"
								>
									<span v-if="file.file">
										<span v-if="file.uploading">
											Uploading
											{{ Math.floor((file.uploaded / file.total) * 100) }}%
										</span>
										<span v-else>Change</span>
									</span>
									<span v-else>Select</span>
								</Button>
							</div>
						</div>
					</div>
				</div>
				<div class="mt-10">
					<label>
						Choose your plan
					</label>
					<p class="text-sm text-gray-600">
						Select a plan based on the type of usage you are expecting on your
						site.
					</p>
					<div class="mt-6">
						<div
							class="px-4 py-2 mb-4 text-sm text-yellow-700 border border-yellow-200 rounded-lg bg-yellow-50"
							v-if="!options.has_subscription"
						>
							You can only create {{ options.trial_sites_count }}
							{{ $plural(options.trial_sites_count, 'site', 'sites') }} in trial
							mode.
							<a href="#/account/billing" class="border-b border-yellow-500">
								Set up your subscription
							</a>
							to create more sites.
						</div>
						<SitePlansTable :plans="options.plans" v-model="selectedPlan" />
					</div>
				</div>
				<div class="mt-6">
					<ErrorMessage v-if="errorMessage">
						{{ errorMessage }}
					</ErrorMessage>
					<Button
						class="w-full mt-2"
						type="primary"
						:disabled="!canCreateSite()"
						@click="createSite"
					>
						Create Site
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import frappeLogo from '@/assets/frappe-framework-logo.png';
import erpnextLogo from '@/assets/erpnext-logo.svg';
import FileUploader from '@/store/fileUploader';
import SitePlansTable from '@/views/partials/SitePlansTable';

export default {
	name: 'NewSite',
	components: {
		SitePlansTable
	},
	data: () => ({
		siteName: null,
		apps: [],
		options: null,
		restoreBackup: false,
		selectedApps: [],
		selectedGroup: null,
		selectedPlan: null,
		selectedFiles: {
			database: null,
			public: null,
			private: null
		},
		siteErrorMessage: null,
		state: null,
		errorMessage: null,
		files: [
			{
				type: 'database',
				title: 'Database Backup',
				uploading: false,
				uploaded: 0,
				total: 1,
				errorMessage: null,
				file: null
			},
			{
				type: 'public',
				title: 'Public Files',
				uploading: false,
				uploaded: 0,
				total: 1,
				errorMessage: null,
				file: null
			},
			{
				type: 'private',
				title: 'Private Files',
				uploading: false,
				uploaded: 0,
				total: 1,
				errorMessage: null,
				file: null
			}
		]
	}),
	async mounted() {
		this.options = await this.$call('press.api.site.options_for_new');
		this.options.plans = this.options.plans.map(plan => {
			plan.disabled = this.disablePlan(plan);
			return plan;
		});
		this.selectedGroup = this.options.groups.find(g => g.default).name;
	},
	watch: {
		selectedGroup() {
			this.selectedApps = [];
			this.updateApps();
		}
	},
	methods: {
		updateApps() {
			let group = this.options.groups.find(g => g.name == this.selectedGroup);
			this.apps = group.apps.map(d => {
				let app = d.scrubbed;
				return {
					app: d.name,
					frappe: d.frappe,
					repo: 'frappe/' + d.scrubbed,
					logo: app === 'frappe' ? frappeLogo : erpnextLogo
				};
			});
			let frappeApp = this.apps.find(a => this.isFrappeApp(a));
			if (frappeApp) {
				this.selectedApps.push(frappeApp.app);
			}
			this.$nextTick(() => {
				this.$refs.siteName.focus();
			});
		},
		async createSite() {
			let siteName = await this.$call('press.api.site.new', {
				site: {
					name: this.siteName,
					apps: this.selectedApps,
					group: this.selectedGroup,
					plan: this.selectedPlan.name,
					files: this.selectedFiles
				}
			});
			this.$router.push(`/sites/${siteName}`);
		},
		isFrappeApp(app) {
			return app.frappe;
		},
		toggleApp(app) {
			if (this.isFrappeApp(app)) return;
			if (!this.selectedApps.includes(app.app)) {
				this.selectedApps.push(app.app);
			} else {
				this.selectedApps = this.selectedApps.filter(a => a !== app.app);
			}
		},
		canCreateSite() {
			return (
				!this.siteErrorMessage &&
				this.siteName &&
				this.selectedApps.length > 0 &&
				this.selectedPlan &&
				this.state !== 'RequestStarted' &&
				(!this.restoreBackup || Object.values(this.selectedFiles).every(v => v))
			);
		},
		async checkIfValid() {
			this.siteErrorMessage = null;
			if (this.siteName.length < 5) {
				this.siteErrorMessage = 'Subdomain too short. Use 5 or more characters';
				return;
			}
			if (this.siteName.length > 32) {
				this.siteErrorMessage = 'Subdomain too long. Use 32 or less characters';
				return;
			}
			if (!this.siteName.match(/^[a-z0-9][a-z0-9-]*[a-z0-9]$/)) {
				this.siteErrorMessage =
					'Subdomain contains invalid characters. Use lowercase characters, numbers and hyphens';
				return;
			}
			if (!this.siteErrorMessage) {
				let exists = await this.$call('press.api.site.exists', {
					subdomain: this.siteName
				});
				if (exists) {
					this.siteErrorMessage = `${this.siteName}.${this.options.domain} already exists.`;
				}
			}
		},
		disablePlan(plan) {
			if (this.options.has_subscription) {
				return false;
			}
			if (this.options.disable_site_creation) {
				return true;
			}
			if (plan.trial_period) {
				return false;
			}
			return true;
		},
		onFile(file, event) {
			file.errorMessage = null;
			file.file = event.target.files[0];
			this.uploadFile(file);
		},
		async uploadFile(file) {
			file.uploader = new FileUploader();
			file.uploader.on('start', () => {
				file.uploading = true;
			});
			file.uploader.on('progress', data => {
				file.uploaded = data.uploaded;
				file.total = data.total;
			});
			file.uploader.on('error', () => {
				file.uploading = false;
			});
			file.uploader.on('finish', () => {
				file.uploading = false;
			});

			file.uploader.upload(file.file, {
				method: 'press.api.site.upload_backup',
				type: file.type
			}).then(result => {
				if (result.status == 'success') {
					this.selectedFiles[file.type] = result.file;
				} else {
					file.file = null;
					file.uploading = false;
					file.errorMessage = result.message;
				}
			}).catch(error => {
					file.file = null;
					file.uploading = false;
					if (error._server_messages) {
						file.errorMessage = JSON.parse(JSON.parse(error._server_messages)[0]).message;
					} else if (error.exc) {
						file.errorMessage = JSON.parse(error.exc)[0].split("\n").slice(-2, -1)[0];
					} else {
						file.errorMessage = "Something Went Wrong";
					}
			});
		}
	}
};
</script>
