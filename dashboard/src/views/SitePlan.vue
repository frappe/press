<template>
	<div>
		<section>
			<h2 class="text-lg font-medium">Plan</h2>
			<p class="text-gray-600">
				Upgrade, downgrade or deactivate this site based on usage
			</p>
			<div
				v-if="currentPlan"
				class="w-full py-4 mt-6 border border-gray-100 rounded shadow sm:w-1/2"
			>
				<div
					class="px-6 py-4 mb-4 hover:bg-gray-50"
					v-if="site.status == 'Active'"
				>
					<div>
						<span class="font-bold">{{ currentPlan.plan_title }} </span>
						(Current Plan)
					</div>
					<div class="text-sm text-gray-800">
						Effective from <FormatDate>{{ lastPlan.timestamp }}</FormatDate>
					</div>
				</div>
				<div class="px-6 mb-4" v-if="site.status == 'Inactive'">
					Your site is deactivated
				</div>
				<div class="px-6 space-x-2">
					<Button
						v-if="site.status == 'Active'"
						type="primary"
						@click="
							() => {
								showChangePlanDialog = true;
								!plans.length && fetchPlans();
							}
						"
					>
						Change Plan
					</Button>
					<Button
						v-if="site.status == 'Active'"
						type="secondary"
						@click="showDeactivateDialog = true"
					>
						Deactivate Site
					</Button>
					<Button
						v-if="site.status == 'Inactive'"
						type="secondary"
						@click="activate"
					>
						Activate Site
					</Button>
				</div>
			</div>
			<Dialog title="Change Plan" v-model="showChangePlanDialog">
				<SitePlansTable class="mt-6" :plans="plans" v-model="selectedPlan" />
				<template slot="actions">
					<Button type="secondary" @click="showChangePlanDialog = false">
						Cancel
					</Button>
					<Button class="ml-2" type="primary" @click="changePlan">
						Submit
					</Button>
				</template>
			</Dialog>
			<Dialog title="Deactivate" v-model="showDeactivateDialog">
				<p>
					Are you sure you want to deactivate this site? The site will go in an
					inactive state. It won't be accessible and background jobs won't run.
					We will also not charge you for it.
				</p>
				<template slot="actions">
					<Button type="secondary" @click="showDeactivateDialog = false">
						Cancel
					</Button>
					<Button class="ml-2" type="danger" @click="deactivate">
						Deactivate
					</Button>
				</template>
			</Dialog>
		</section>
		<section class="mt-10">
			<h2 class="text-lg font-medium">Usage</h2>
			<p class="text-gray-600">
				Calculated usage of this site updated every hour
			</p>
			<div
				v-if="currentPlan"
				class="w-full py-4 mt-6 border border-gray-100 rounded shadow sm:w-1/2"
			>
				<div class="flex px-6 py-4 hover:bg-gray-50">
					<!-- <div class="w-1/2">
						<div class="font-bold">
							$40
						</div>
						<div class="text-sm text-gray-800">
							Since April 17, 2020
						</div>
					</div> -->
					<div class="w-1/2 text-sm">
						<div class="leading-6">
							<span class="font-bold"> {{ totalCPUUsage }} hours </span>
							/ {{ currentPlan.cpu_time_per_day }} hours CPU usage
						</div>
						<div class="text-gray-800">
							Cycle resets in {{ hoursUntilReset }} hours
						</div>
					</div>
				</div>
			</div>
		</section>
		<section class="mt-10">
			<h2 class="text-lg font-medium">History</h2>
			<p class="text-gray-600">
				Log of plan changes for this site
			</p>
			<div
				class="w-full py-4 mt-6 border border-gray-100 rounded shadow sm:w-1/2"
			>
				<div
					class="px-6 py-4 hover:bg-gray-50"
					v-for="row in history"
					:key="row.name"
				>
					<div v-if="row.type == 'Initial Plan'">
						Site created with {{ row.to_plan }} plan
					</div>
					<div v-else-if="row.type == 'Downgrade'">
						Site downgraded to {{ row.to_plan }} plan
					</div>
					<div v-else-if="row.type == 'Upgrade'">
						Site upgraded to {{ row.to_plan }} plan
					</div>
					<div class="text-sm text-gray-800">
						<FormatDate>{{ row.timestamp }}</FormatDate>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import Dialog from '@/components/Dialog';
import SitePlansTable from '@/views/partials/SitePlansTable';

export default {
	name: 'SitePlan',
	props: ['site'],
	components: {
		Dialog,
		SitePlansTable
	},
	data() {
		return {
			currentPlan: null,
			totalCPUUsage: 0,
			hoursUntilReset: 0,
			history: [],
			showChangePlanDialog: false,
			plans: [],
			selectedPlan: null,
			showDeactivateDialog: false
		};
	},
	mounted() {
		this.fetchCurrentPlan();
	},
	methods: {
		async fetchCurrentPlan() {
			let out = await this.$call('press.api.site.current_plan', {
				name: this.site.name
			});
			this.currentPlan = out.current_plan;
			this.history = out.history;
			this.totalCPUUsage = out.total_cpu_usage_hours;
			this.hoursUntilReset = out.hours_until_reset;
		},
		async fetchPlans() {
			this.plans = await this.$call('press.api.site.get_plans');
			this.plans = this.plans.map(plan => {
				if (this.currentPlan.name === plan.name) {
					plan.disabled = true;
				}
				return plan;
			});
		},
		async changePlan() {
			await this('press.api.site.change_plan', {
				name: this.site.name,
				plan: this.selectedPlan.name
			});
			this.$notify({
				title: `Plan changed to ${this.selectedPlan.plan_title}`,
				icon: 'check',
				color: 'green'
			});
			this.showChangePlanDialog = false;
			this.selectedPlan = null;
			this.fetchCurrentPlan();
			this.fetchPlans();
		},
		deactivate() {
			this.$call('press.api.site.deactivate', {
				name: this.site.name
			});
			this.showDeactivateDialog = false;
			setTimeout(() => window.location.reload(), 1000);
		},
		activate() {
			this.$call('press.api.site.activate', {
				name: this.site.name
			});
			this.$notify({
				title: 'Site activated successfully!',
				message: 'You can now access your site',
				icon: 'check',
				color: 'green'
			});
			setTimeout(() => window.location.reload(), 1000);
		}
	},
	computed: {
		lastPlan() {
			return this.history ? this.history[0] : null;
		}
	}
};
</script>
