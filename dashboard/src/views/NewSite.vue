<template>
	<div>
		<PageHeader>
			<h1 slot="title">New Site</h1>
		</PageHeader>
		<div class="px-8" v-if="options">
			<div class="border-t mb-5"></div>
			<div
				class="rounded-lg border border-gray-100 shadow-md mx-auto px-6 py-8"
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
					<div class="mt-6 flex">
						<input
							class="form-input rounded-r-none z-10 bg-gray-50 focus:bg-white w-full"
							type="text"
							v-model="siteName"
							@change="checkIfExists"
							placeholder="subdomain"
							ref="siteName"
						/>
						<div class="bg-gray-200 flex border items-center px-4 rounded-r">
							.{{ options.domain }}
						</div>
					</div>
					<div class="mt-1 text-red-600 text-sm" v-if="siteExistsMessage">
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
					<div class="mt-6 flex">
						<button
							class="rounded px-6 py-8 border w-40 mr-4 flex justify-center items-center cursor-pointer focus:outline-none focus:shadow-outline"
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
								<img class="mx-auto w-8 h-8" :src="app.logo" :alt="app.name" />
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
					<div class="mt-6 flex overflow-auto py-1 pl-1 -ml-1">
						<button
							class="rounded border text-center w-40 mr-4 cursor-pointer flex-shrink-0 focus:outline-none focus:shadow-outline"
							:class="
								selectedPlan === plan
									? 'bg-blue-100 border-blue-500'
									: 'hover:bg-gray-100'
							"
							v-for="plan in plans"
							:key="plan.price"
							@click="selectedPlan = plan"
						>
							<div class="border-b py-3">
								<span class="font-semibold text-base"> ${{ plan.price }} </span>
								<span class="text-gray-600">
									/mo
								</span>
							</div>
							<div class="py-3 text-sm text-gray-600">
								<div v-for="d in plan.items" :key="d">{{ d }}</div>
							</div>
						</button>
					</div>
				</div>
				<div class="mt-10">
					<label class="flex leading-none py-2">
						<input
							type="checkbox"
							class="form-checkbox"
							v-model="enableBackups"
						/>
						<span class="ml-2">
							Enable Backups
						</span>
					</label>
					<label class="flex leading-none py-2">
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
				<Button
					class="mt-10 bg-brand text-white text-sm w-full focus:bg-blue-600"
					:disabled="canCreateSite()"
					@click="createSite"
				>
					Create Site
				</Button>
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
		plans: [
			{
				price: 5,
				items: ['5000 emails', '5GB storage']
			},
			{
				price: 10,
				items: ['15000 emails', '10GB storage']
			},
			{
				price: 30,
				items: ['30000 emails', '30GB storage']
			},
			{
				price: 50,
				items: ['50000 emails', '50GB storage']
			},
			{
				price: 100,
				items: ['100000 emails', '200GB storage']
			}
		]
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
		this.selectedPlan = this.plans[0];
		this.$nextTick(() => {
			this.$refs.siteName.focus();
		});
	},
	methods: {
		async createSite() {
			this.state = 'Creating Site';
			let siteName = await this.$call('press.api.site.new', {
				site: {
					name: this.siteName,
					apps: this.selectedApps,
					backups: this.enableBackups,
					monitor: this.enableMonitoring,
					group: this.options.group
				}
			});
			this.state = null;
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
