<template>
	<div class="mt-5">
		<div class="px-8" v-if="options">
			<div
				class="p-8 mx-auto mb-20 space-y-8 border rounded-lg shadow-md"
				style="width: 650px"
			>
				<div>
					<h1 class="mb-6 text-2xl font-bold">Create a New Site</h1>
					<label class="text-lg">
						Choose a hostname
					</label>
					<p class="text-base text-gray-700">
						Give your site a unique name. It can only contain alphanumeric
						characters and dashes.
					</p>
					<div class="flex mt-4">
						<input
							class="z-10 w-full rounded-r-none form-input "
							type="text"
							v-model="siteName"
							placeholder="subdomain"
							ref="siteName"
							@change="checkIfExists"
						/>
						<div class="flex items-center px-4 text-base bg-gray-100 rounded-r">
							.{{ options.domain }}
						</div>
					</div>
					<ErrorMessage class="mt-1" :error="subdomainInvalidMessage" />
				</div>
				<div>
					<label class="text-lg">
						Choose your apps
					</label>
					<p class="text-base text-gray-700">
						Select apps to install to your site. You can also choose a specific
						version of the app.
					</p>
					<div class="mt-4">
						<Input
							type="select"
							v-model="selectedGroup"
							:options="groupOptions"
						/>
					</div>
					<div class="mt-6">
						<div class="flex py-2 pl-1 -my-2 -ml-1 overflow-x-auto">
							<button
								class="relative flex items-center justify-center py-4 pl-4 pr-8 mr-4 border rounded-md cursor-pointer focus:outline-none focus:shadow-outline"
								:class="
									selectedApps.includes(app.app)
										? 'bg-blue-50 border-blue-500'
										: 'hover:border-blue-400'
								"
								v-for="app in apps"
								:key="app.app"
								@click="toggleApp(app)"
							>
								<div class="flex items-start">
									<Input
										class="pt-0.5 pointer-events-none"
										tabindex="-1"
										type="checkbox"
										:value="selectedApps.includes(app.app)"
									/>
									<div class="ml-3 text-base text-left">
										<div class="font-semibold">
											{{ app.repo_owner }}/{{ app.repo }}
										</div>
										<div class="text-gray-700">
											{{ app.branch }}
										</div>
									</div>
								</div>
							</button>
						</div>
					</div>
				</div>
				<div>
					<label class="flex py-2 leading-none">
						<Input
							label="Create Site from Backup"
							type="checkbox"
							v-model="restoreBackup"
						/>
					</label>
					<p class="text-base text-gray-700">
						Upload backup files instead of starting from a blank site.
					</p>
					<div class="flex grid grid-cols-3 gap-4 mt-6" v-if="restoreBackup">
						<FileUploader
							v-for="file in files"
							:key="file.type"
							@success="onFileUpload(file, $event)"
							:upload-args="{
								method: 'press.api.site.upload_backup',
								type: file.type
							}"
						>
							<template
								v-slot="{
									file: fileObj,
									uploading,
									progress,
									error,
									success,
									openFileSelector
								}"
							>
								<button
									class="w-full h-full px-4 py-6 border rounded-md focus:outline-none focus:shadow-outline hover:border-blue-400"
									:class="success ? 'bg-blue-50 border-blue-500' : ''"
									@click="openFileSelector()"
									:disabled="uploading"
								>
									<FeatherIcon
										:name="success ? 'check' : file.icon"
										class="inline-block w-5 h-5 text-gray-700"
									/>
									<div
										class="mt-3 text-base font-semibold leading-none text-gray-800"
									>
										{{ file.title }}
									</div>
									<div
										class="mt-2 text-xs leading-snug text-gray-700"
										v-if="fileObj"
									>
										{{ fileObj.name }}
									</div>
									<div class="text-base" v-if="progress && progress !== 100">
										{{ progress }} %
									</div>
									<div class="mt-2 text-sm text-red-600" v-if="error">
										{{ error }}
									</div>
									<div class="mt-2 text-xs text-gray-500" v-if="!progress">
										Click to upload
									</div>
								</button>
							</template>
						</FileUploader>
					</div>
				</div>
				<div>
					<label class="text-lg">
						Choose your plan
					</label>
					<p class="text-base text-gray-700">
						Select a plan based on the type of usage you are expecting on your
						site.
					</p>
					<div class="mt-4">
						<Alert class="mb-4" v-if="showAlert">
							You have not added your billing information.
							<router-link to="/welcome" class="border-b border-yellow-500"
								>Add your billing information</router-link
							>
							to create sites.
						</Alert>
						<SitePlansTable :plans="options.plans" v-model="selectedPlan" />
					</div>
				</div>
				<div>
					<ErrorMessage :error="errorMessage" />
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
import FileUploader from '@/components/FileUploader';
import SitePlansTable from '@/views/partials/SitePlansTable';

export default {
	name: 'NewSite',
	components: {
		FileUploader,
		SitePlansTable
	},
	data: () => ({
		siteName: null,
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
		subdomainTaken: false,
		state: null,
		errorMessage: null,
		files: [
			{
				icon: 'database',
				type: 'database',
				title: 'Database Backup',
				file: null
			},
			{
				icon: 'file',
				type: 'public',
				title: 'Public Files',
				file: null
			},
			{
				icon: 'file-minus',
				type: 'private',
				title: 'Private Files',
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
		if (this.$route.query.domain) {
			let domain = this.$route.query.domain.split('.');
			if (domain) {
				this.siteName = domain[0];
			}
			this.$router.replace({});
		}
	},
	watch: {
		selectedGroup: {
			handler: 'resetAppSelection',
			immediate: true
		}
	},
	computed: {
		showAlert() {
			return (
				this.options &&
				!this.options.free_account &&
				!this.options.has_card &&
				!this.options.allow_partner
			);
		},
		groupOptions() {
			return this.options.groups.map(option => option.name);
		},
		apps() {
			if (!this.options) return [];

			let group = this.options.groups.find(g => g.name == this.selectedGroup);
			return group.apps;
		},
		subdomainInvalidMessage() {
			if (!this.siteName) {
				return '';
			}
			if (this.siteName.length < 5) {
				return 'Subdomain too short. Use 5 or more characters';
			}
			if (this.siteName.length > 32) {
				return 'Subdomain too long. Use 32 or less characters';
			}
			if (!this.siteName.match(/^[a-z0-9][a-z0-9-]*[a-z0-9]$/)) {
				return 'Subdomain contains invalid characters. Use lowercase characters, numbers and hyphens';
			}
			if (this.subdomainTaken) {
				return `${this.siteName}.${this.options.domain} already exists.`;
			}
			return '';
		}
	},
	methods: {
		resetAppSelection() {
			this.selectedApps = [];
			let frappeApp = this.apps.find(app => app.frappe);
			if (frappeApp) {
				this.selectedApps.push(frappeApp.app);
			}
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
		toggleApp(app) {
			if (app.frappe) return;
			if (!this.selectedApps.includes(app.app)) {
				this.selectedApps.push(app.app);
			} else {
				this.selectedApps = this.selectedApps.filter(a => a !== app.app);
			}
		},
		canCreateSite() {
			return (
				!this.subdomainInvalidMessage &&
				this.siteName &&
				this.selectedApps.length > 0 &&
				this.selectedPlan &&
				this.state !== 'RequestStarted' &&
				(!this.restoreBackup || Object.values(this.selectedFiles).every(v => v))
			);
		},
		async checkIfExists() {
			this.subdomainTaken = await this.$call('press.api.site.exists', {
				subdomain: this.siteName
			});
		},
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
		},
		onFileUpload(file, fileurl) {
			this.selectedFiles[file.type] = fileurl;
		}
	}
};
</script>
