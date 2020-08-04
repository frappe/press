<template>
	<div class="mt-5">
		<div class="px-8" v-if="options">
			<div
				class="p-8 mx-auto mb-20 space-y-8 border rounded-lg shadow-md"
				style="width: 650px"
			>
				<div>
					<h1 class="mb-6 text-2xl font-bold text-center">Create a New Site</h1>
					<div class="flex items-center justify-center ">
						<div class="flex space-x-8">
							<div
								class="relative"
								v-for="(step, index) in steps"
								:key="step.name"
							>
								<div
									class="z-10 flex items-center justify-center w-5 h-5 bg-white border border-gray-400 rounded-full"
									:class="{
										'bg-blue-500 text-white': step.completed,
										'border-blue-500': step.current || step.completed
									}"
								>
									<FeatherIcon
										v-if="step.completed"
										name="check"
										class="w-3 h-3"
										:stroke-width="3"
									/>
									<div
										class="w-1.5 h-1.5 bg-blue-500 rounded-full"
										v-if="step.current"
									></div>
								</div>
								<div
									class="absolute w-8 transform -translate-x-8 -translate-y-1/2 border-t border-gray-400 top-1/2"
									:class="{ 'border-blue-500': step.completed || step.current }"
									v-show="index !== 0"
								></div>
							</div>
						</div>
					</div>
				</div>
				<div v-show="currentStep.name === 'Hostname'">
					<label class="text-lg font-semibold">
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
				<div v-show="currentStep.name === 'Apps'">
					<label class="text-lg font-semibold">
						Select apps to install
					</label>
					<p class="text-base text-gray-700">
						Choose apps to install on your site. You can also choose a specific
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
									selectedApps.includes(app.name)
										? 'bg-blue-50 border-blue-500'
										: 'hover:border-blue-400'
								"
								v-for="app in apps"
								:key="app.name"
								@click="toggleApp(app)"
							>
								<div class="flex items-start">
									<Input
										class="pt-0.5 pointer-events-none"
										tabindex="-1"
										type="checkbox"
										:value="selectedApps.includes(app.name)"
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
				<div v-show="currentStep.name == 'Restore'">
					<label class="text-lg font-semibold">
						Restore an existing site
					</label>
					<p class="text-base text-gray-700">
						Restore an existing site from backup files or directly from site
						url.
					</p>
					<div class="flex mt-4 space-x-8">
						<button
							v-for="tab in [
								{ name: 'Upload Backups', key: 'backup' },
								{ name: 'Migrate from Site URL', key: 'siteUrl' }
							]"
							:key="tab.key"
							class="block px-1 py-4 text-base font-medium leading-none truncate border-b focus:outline-none"
							:class="
								restoreFrom === tab.key
									? 'border-brand text-gray-900'
									: 'text-gray-600 hover:text-gray-900 border-transparent'
							"
							@click="restoreFrom = tab.key"
						>
							{{ tab.name }}
						</button>
					</div>
					<div v-if="restoreFrom === 'backup'">
						<div class="grid grid-cols-3 gap-4 mt-6">
							<FileUploader
								v-for="file in files"
								:fileTypes="file.ext"
								:key="file.type"
								:type="file.type"
								:s3="true"
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
										message,
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
										<div
											class="mt-2 text-xs text-gray-500"
											v-if="!(progress || error) || message"
										>
											{{ message || 'Click to upload' }}
										</div>
									</button>
								</template>
							</FileUploader>
						</div>
					</div>
					<div v-if="restoreFrom === 'siteUrl'">
						<div class="mt-6">
							<Form
								:fields="[
									{
										label: 'Site URL',
										fieldtype: 'Data',
										fieldname: 'url'
									},
									{
										label: 'Email',
										fieldtype: 'Data',
										fieldname: 'email'
									},
									{
										label: 'Password',
										fieldtype: 'Password',
										fieldname: 'password'
									}
								]"
								v-model="frappeSite"
							/>
							<!-- <Input
								label="Site URL"
								type="text"
								placeholder="example.com"
								v-model="frappeSite"
							/> -->
							<ErrorMessage class="mt-1 ml-1" :error="invalidFrappeSite" />
							<!-- <Input
								class="mt-4"
								label="Email"
								type="email"
								placeholder="user@example.com"
								v-model="userNameFrappeSite"
							/>
							<Input
								class="mt-4"
								label="Password"
								type="password"
								placeholder="********"
								v-model="passwordFrappeSite"
							/> -->
							<ErrorMessage class="mt-3" :error="invalidAccountCredentials" />
							<ErrorMessage class="mt-3" :error="incompatibleSite" />
							<ErrorMessage class="mt-3" :error="magicalError" />
							<SuccessMessage class="mt-3" :success="receivedBackups" />
							<FeatherIcon
								name="check"
								class="w-5 h-5 p-1 mr-2 text-green-500 bg-green-100 rounded-full"
								v-if="
									!(
										((selectedFiles.database == selectedFiles.public) ==
											selectedFiles.private) !=
										null
									)
								"
							/>
						</div>
					</div>
				</div>
				<div v-show="currentStep.name === 'Plan'">
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
					<div class="flex justify-between">
						<Button @click="backStep" v-show="currentStep.name != 'Hostname'">
							Back
						</Button>
						<Button
							type="primary"
							@click="nextStep"
							v-show="currentStep.name != 'Plan'"
						>
							Next
						</Button>
					</div>
					<Button
						v-show="currentStep.name === 'Plan'"
						class="w-full mt-2"
						type="primary"
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
import Form from '@/components/Form';

export default {
	name: 'NewSite',
	components: {
		FileUploader,
		SitePlansTable,
		Form
	},
	data: () => ({
		siteName: null,
		options: null,
		restoreFrom: 'backup', // backup, siteUrl
		restoreBackup: false,
		migrateFromSelfHosted: false,
		magicalErrorOccurred: false,
		frappeSite: {
			url: '',
			email: '',
			password: ''
		},
		verifiedFrappeSite: null,
		validFrappeSiteCredentials: null,
		incompatibleFrappeSite: null,
		userNameFrappeSite: null,
		passwordFrappeSite: null,
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
				ext: 'application/x-gzip',
				title: 'Database Backup',
				file: null
			},
			{
				icon: 'file',
				type: 'public',
				ext: 'application/x-tar',
				title: 'Public Files',
				file: null
			},
			{
				icon: 'file-minus',
				type: 'private',
				ext: 'application/x-tar',
				title: 'Private Files',
				file: null
			}
		],
		steps: [
			{
				name: 'Hostname',
				current: true,
				completed: false
			},
			{
				name: 'Apps',
				current: false,
				completed: false
			},
			{
				name: 'Restore',
				skippable: true,
				current: false,
				completed: false
			},
			{
				name: 'Plan',
				current: false,
				completed: false
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
		},
		invalidFrappeSite() {
			if (this.frappeSite && this.verifiedFrappeSite === false) {
				return `${this.frappeSite} is not a valid Frappe Site`;
			}
		},
		invalidAccountCredentials() {
			if (
				!this.incompatibleFrappeSite &&
				this.validFrappeSiteCredentials === false
			) {
				return 'Invalid Credentials or Insufficient Permissions';
			}
		},
		incompatibleSite() {
			if (this.incompatibleFrappeSite === true) {
				return `Update your site ${this.frappeSite} to use this feature or use a different site creation method`;
			}
		},
		receivedBackups() {
			if (this.validFrappeSiteCredentials === true) {
				return 'Selected Backup Files';
			}
		},
		magicalError() {
			if (this.magicalErrorOccurred === true) {
				return 'An Internal Error has occurred. Use another method or contact support';
			}
		},
		currentStep() {
			return this.steps.find(step => step.current);
		}
	},
	methods: {
		resetAppSelection() {
			this.selectedApps = [];
			let frappeApp = this.apps.find(app => app.frappe);
			if (frappeApp) {
				this.selectedApps.push(frappeApp.name);
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
			if (!this.selectedApps.includes(app.name)) {
				this.selectedApps.push(app.name);
			} else {
				this.selectedApps = this.selectedApps.filter(a => a !== app.name);
			}
		},
		selectMethod(method) {
			this.method = method;
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
		},
		async verifySite() {
			this.verifiedFrappeSite = null;
			let result = await this.$call('press.api.site.verify', {
				site: this.frappeSite
			});
			let { status } = result;
			this.verifiedFrappeSite = status;
		},
		async getBackup() {
			if (
				!(this.frappeSite && this.userNameFrappeSite && this.passwordFrappeSite)
			) {
				return false;
			}
			let { site, files, status, exc } = await this.$call(
				'press.api.site.get_backup_links',
				{
					site: this.frappeSite,
					auth: {
						usr: this.userNameFrappeSite,
						pwd: this.passwordFrappeSite
					}
				}
			);

			this.validFrappeSiteCredentials = status.toString()[0] == '2';
			this.magicalErrorOccurred = status.toString()[0] == '5';
			this.incompatibleFrappeSite = status == 404;

			if (this.validFrappeSiteCredentials) {
				for (let file of Object.keys(files)) {
					let map = files[file].split('/');
					let name = map[map.length - 1].split('?')[0];
					let upload = await this.$call('press.api.site.uploaded_backup_info', {
						file: name,
						url: files[file],
						type:
							file === 'database' ? 'application/x-gzip' : 'application/x-tar'
					});
					this.selectedFiles[file] = upload;
				}
			}
		},
		nextStep() {
			let currentStepIndex = this.steps.findIndex(step => step.current);
			this.steps[currentStepIndex].current = false;
			this.steps[currentStepIndex].completed = true;
			this.steps[currentStepIndex + 1].current = true;
		},
		backStep() {
			let currentStepIndex = this.steps.findIndex(step => step.current);
			this.steps[currentStepIndex].current = false;
			this.steps[currentStepIndex - 1].current = true;
			this.steps[currentStepIndex - 1].completed = false;
		}
	}
};
</script>
