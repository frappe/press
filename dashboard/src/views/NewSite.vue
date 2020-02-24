<template>
	<div>
		<PageHeader>
			<h1 slot="title">New Site</h1>
		</PageHeader>
		<div class="px-8">
			<div class="border-t mb-5"></div>
			<div class="rounded-lg shadow-md mx-auto px-6 py-8" style="width: 650px">
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
							class="form-input rounded-r-none z-10 bg-gray-100 focus:bg-white w-full"
							type="text"
							v-model="siteName"
						/>
						<div class="bg-gray-200 flex border items-center px-4 rounded-r">
							.frappe.cloud
						</div>
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
						<div
							class="rounded px-6 py-8 border w-40 mr-4 flex justify-center items-center cursor-pointer"
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
									{{ app.name }}
								</div>
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
					<div class="mt-6 flex overflow-auto">
						<div
							class="rounded border text-center w-40 mr-4 cursor-pointer flex-shrink-0"
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
						</div>
					</div>
				</div>
				<div class="mt-10">
					<label class="flex leading-none">
						<input type="checkbox" class="form-checkbox" />
						<span class="ml-2">
							Enable Backups
						</span>
					</label>
				</div>
				<Button
					class="mt-10 text-white text-sm w-full"
					:class="
						canCreateSite() ? 'bg-blue-500' : 'bg-blue-300 pointer-events-none'
					"
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
		bench: 'faris2-bench',
		server: 'f1.frappe.cloud',
		siteName: null,
		apps: [],
		selectedApps: [],
		selectedPlan: null,
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
		let bench = await this.$call('frappe.client.get', {
			doctype: 'Bench',
			name: this.bench
		});
		this.apps = bench.apps.map(d => {
			let app = d.scrubbed;
			return {
				app: d.app,
				name: 'frappe/' + d.scrubbed,
				logo: app === 'frappe' ? frappeLogo : erpnextLogo
			};
		});
		let frappeApp = this.apps.find(a => this.isFrappeApp(a));
		if (frappeApp) {
			this.selectedApps.push(frappeApp.app);
		}
		this.selectedPlan = this.plans[0];
	},
	methods: {
		async createSite() {
			let siteName = this.siteName + '.frappe.cloud';
			let res = await this.$call('frappe.client.insert', {
				doc: {
					doctype: 'Site',
					name: siteName,
					bench: this.bench,
					server: this.server,
					apps: this.selectedApps.map(app => {
						return { app };
					})
				}
			});
			if (!res.error) {
				this.$router.push(`/sites/${siteName}`);
			}
		},
		isFrappeApp(app) {
			return app.app.toLowerCase().includes('frappe');
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
			return this.siteName && this.selectedApps.length > 0 && this.selectedPlan;
		}
	}
};
</script>
