<template>
	<div
		v-if="$site?.doc"
		class="grid grid-cols-1 items-start gap-5 lg:grid-cols-2"
	>
		<AlertBanner
			v-if="!isSetupWizardComplete"
			class="col-span-1 lg:col-span-2"
			title="Please login and complete the setup wizard on your site. Analytics will be
			collected only after setup is complete."
		>
			<Button
				class="ml-auto"
				variant="outline"
				@click="loginAsAdmin"
				:loading="$site.loginAsAdmin.loading"
			>
				Login
			</Button>
		</AlertBanner>
		<div class="col-span-1 rounded-md border lg:col-span-2">
			<div class="grid grid-cols-2 lg:grid-cols-4">
				<div class="border-b border-r p-5 lg:border-b-0">
					<div class="text-base text-gray-700">Current Plan</div>
					<div class="mt-2 flex items-start justify-between">
						<div>
							<div class="leading-4">
								<span class="text-base text-gray-900" v-if="currentPlan">
									{{ $format.planTitle(currentPlan) }}
									<span v-if="currentPlan.price_inr">/ month</span>
								</span>
								<span class="text-base text-gray-900" v-else>
									No plan set
								</span>
							</div>
							<div
								class="mt-1 text-sm leading-3 text-gray-600"
								v-if="currentPlan"
							>
								{{
									currentPlan.support_included
										? 'Support included'
										: 'Support not included'
								}}
							</div>
						</div>
						<Button @click="showPlanChangeDialog">Change</Button>
					</div>
				</div>
				<div class="border-b p-5 lg:border-b-0 lg:border-r">
					<div class="text-base text-gray-700">Compute</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.cpu / currentPlan.cpu_time_per_day) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ currentUsage.cpu }}
									{{ $format.plural(currentUsage.cpu, 'hour', 'hours') }}
									<template v-if="currentPlan">
										of {{ currentPlan?.cpu_time_per_day }} hours
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="border-r p-5">
					<div class="text-base text-gray-700">Storage</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.storage / currentPlan.max_storage_usage) * 100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ formatBytes(currentUsage.storage) }}
									<template v-if="currentPlan">
										of {{ formatBytes(currentPlan.max_storage_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="p-5">
					<div class="text-base text-gray-700">Database</div>
					<div class="mt-2">
						<Progress
							size="md"
							:value="
								currentPlan
									? (currentUsage.database / currentPlan.max_database_usage) *
									  100
									: 0
							"
						/>
						<div>
							<div class="mt-2 flex justify-between">
								<div class="text-sm text-gray-600">
									{{ formatBytes(currentUsage.database) }}
									<template v-if="currentPlan">
										of
										{{ formatBytes(currentPlan.max_database_usage) }}
									</template>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">Site Information</h2>
			</div>
			<div>
				<div
					v-for="d in siteInformation"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base text-gray-600">{{ d.label }}</div>
					<div
						class="flex w-2/3 items-center space-x-2 text-base text-gray-900"
					>
						<span>
							{{ d.value }}
						</span>
						<div v-if="d.help">
							<Tooltip :text="d.help">
								<i-lucide-info class="h-4 w-4 text-gray-500" />
							</Tooltip>
						</div>
					</div>
				</div>
			</div>
		</div>
		<SiteDailyUsage :site="site" />
	</div>
</template>
<script>
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource, Progress } from 'frappe-ui';
import { renderDialog } from '../utils/components';
import SiteDailyUsage from './SiteDailyUsage.vue';
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'SiteOverview',
	props: ['site'],
	components: { SiteDailyUsage, Progress, AlertBanner },
	data() {
		return {
			isSetupWizardComplete: true
		};
	},
	mounted() {
		if (this.$site?.doc?.status === 'Active') {
			this.$site.isSetupWizardComplete.submit().then(res => {
				this.isSetupWizardComplete = res;
			});
		}
	},
	methods: {
		showPlanChangeDialog() {
			let SitePlansDialog = defineAsyncComponent(() =>
				import('../components/ManageSitePlansDialog.vue')
			);
			renderDialog(h(SitePlansDialog, { site: this.site }));
		},
		formatBytes(v) {
			return this.$format.bytes(v, 2, 2);
		},
		loginAsAdmin() {
			this.$site.loginAsAdmin.submit().then(url => window.open(url, '_blank'));
		}
	},
	computed: {
		siteInformation() {
			return [
				{
					label: 'Owned by',
					value: this.$site.doc.owner_email
				},
				{
					label: 'Created by',
					value: this.$site.doc.owner
				},
				{
					label: 'Created on',
					value: this.$format.date(this.$site.doc.creation)
				},
				{
					label: 'Inbound IP',
					value: this.$site.doc.inbound_ip,
					help: 'Use this for adding A records for your site'
				},
				{
					label: 'Outbound IP',
					value: this.$site.doc.outbound_ip,
					help: 'Use this for whitelisting our server on a 3rd party service'
				}
			];
		},
		currentPlan() {
			if (!this.$site.doc.current_plan) return null;
			let currency = this.$team.doc.currency;
			return {
				price:
					currency === 'INR'
						? this.$site.doc.current_plan.price_inr
						: this.$site.doc.current_plan.price_usd,
				price_per_day:
					currency === 'INR'
						? this.$site.doc.current_plan.price_per_day_inr
						: this.$site.doc.current_plan.price_per_day_usd,
				currency: currency == 'INR' ? '₹' : '$',
				...this.$site.doc.current_plan
			};
		},
		currentUsage() {
			return this.$site.doc.current_usage;
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	}
};
</script>
