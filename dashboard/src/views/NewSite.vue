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
							@change="checkIfExists"
							placeholder="subdomain"
							ref="siteName"
						/>
						<div class="flex items-center px-4 bg-gray-200 border rounded-r">
							.{{ options.domain }}
						</div>
					</div>
					<div class="mt-1 text-sm text-red-600" v-if="siteExistsMessage">
						{{ siteExistsMessage }}
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
					<div class="flex mt-6">
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
								<img class="w-8 h-8 mx-auto" :src="app.logo" :alt="app.name" />
								<div class="mt-3 font-semibold">
									{{ app.repo }}
								</div>
							</div>
						</button>
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
							class="flex px-4 py-3 text-sm text-gray-600 border border-b-0 bg-gray-50 rounded-t-md"
						>
							<div class="w-10"></div>
							<div class="w-1/3">Plan</div>
							<div class="w-1/3">Concurrent Users</div>
							<div class="w-1/3">CPU Time</div>
						</div>
						<div
							class="flex px-4 py-3 text-sm text-left border border-b-0 cursor-pointer focus-within:shadow-outline"
							:class="[
								selectedPlan === plan ? 'bg-blue-100' : 'hover:bg-blue-50',
								{ 'border-b rounded-b-md': i === options.plans.length - 1 }
							]"
							v-for="(plan, i) in options.plans"
							:key="plan.name"
							@click="selectedPlan = plan"
						>
							<div class="flex items-center w-10">
								<input
									type="radio"
									class="form-radio"
									:checked="selectedPlan === plan"
									@change="e => (selectedPlan = e.target.checked ? plan : null)"
								/>
							</div>
							<div class="w-1/3">
								<span class="font-semibold">
									{{ plan.plan_title }}
								</span>
								<span> /mo</span>
							</div>
							<div class="w-1/3 text-gray-700">
								{{ plan.concurrent_users }}
								{{ $plural(plan.concurrent_users, 'user', 'users') }}
							</div>
							<div class="w-1/3 text-gray-700">
								{{ plan.cpu_time_per_day }}
								{{ $plural(plan.concurrent_users, 'hour', 'hours') }} / day
							</div>
						</div>
					</div>
					<div class="mt-2 text-sm text-gray-900" v-if="selectedPlan">
						This plan is ideal for
						{{ selectedPlan.concurrent_users }} concurrent
						{{ $plural(selectedPlan.concurrent_users, 'user', 'users') }}. It
						will allow the CPU execution time equivalent to
						{{ selectedPlan.cpu_time_per_day }}
						{{ $plural(selectedPlan.cpu_time_per_day, 'hour', 'hours') }} per
						day.
					</div>
				</div>
				<div class="mt-10">
					<label class="flex py-2 leading-none">
						<input
							type="checkbox"
							class="form-checkbox"
							v-model="enableBackups"
						/>
						<span class="ml-2">
							Enable Backups
						</span>
					</label>
					<label class="flex py-2 leading-none">
						<input
							type="checkbox"
							class="form-checkbox"
							v-model="enableMonitoring"
						/>
						<span class="ml-2">
							Enable Uptime Monitoring
						</span>
					</label>
				</div>
				<div class="mt-10">
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

export default {
	name: 'NewSite',
	data: () => ({
		siteName: null,
		apps: [],
		enableBackups: false,
		enableMonitoring: false,
		options: null,
		selectedApps: [],
		selectedPlan: null,
		siteExistsMessage: null,
		state: null,
		errorMessage: null
	}),
	async mounted() {
		this.options = await this.$call('press.api.site.options_for_new');
		this.apps = this.options.apps.map(d => {
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
	methods: {
		async createSite() {
			this.state = 'Creating Site';
			try {
				let siteName = await this.$call('press.api.site.new', {
					site: {
						name: this.siteName,
						apps: this.selectedApps,
						backups: this.enableBackups,
						monitor: this.enableMonitoring,
						group: this.options.group,
						plan: this.selectedPlan.name
					}
				});
				this.$router.push(`/sites/${siteName}`);
			} catch (error) {
				this.errorMessage = error.messages.join('\n');
			}
			this.state = null;
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
				!this.siteExistsMessage &&
				this.siteName &&
				this.selectedApps.length > 0 &&
				this.selectedPlan &&
				this.state !== 'Creating Site'
			);
		},
		async checkIfExists() {
			let exists = await this.$call('press.api.site.exists', {
				subdomain: this.siteName
			});
			this.siteExistsMessage = exists
				? `${this.siteName}.${this.options.domain} already exists.`
				: null;
		}
	}
};
</script>
