<template>
	<div>
		<Section
			title="Plan"
			description="Upgrade, downgrade or deactivate this site based on usage"
		>
			<SectionCard v-if="currentPlan">
				<div class="px-6 py-4 mb-2 text-base hover:bg-gray-50">
					<div class="leading-6 text-gray-900">
						<span class="font-bold">{{ currentPlan.plan_title }} </span>
						(Current Plan)
					</div>
					<div class="text-gray-600">
						Effective from <FormatDate>{{ lastPlan.timestamp }}</FormatDate>
					</div>
				</div>
				<div class="px-6 my-2 text-base" v-if="site.status == 'Inactive'">
					Your site is deactivated
				</div>
				<div class="px-6 my-2 text-base" v-if="site.status == 'Suspended'">
					Your site has been suspended
				</div>
				<div class="px-6 pb-2 space-x-2">
					<Button
						v-if="['Active', 'Suspended'].includes(site.status)"
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
			</SectionCard>
			<Dialog title="Change Plan" v-model="showChangePlanDialog">
				<SitePlansTable class="mt-6" :plans="plans" v-model="selectedPlan" />
				<ErrorMessage class="mt-4" :error="$resources.changePlan.error" />
				<template slot="actions">
					<Button type="secondary" @click="showChangePlanDialog = false">
						Cancel
					</Button>
					<Button
						class="ml-2"
						type="primary"
						@click="$resources.changePlan.submit()"
					>
						Submit
					</Button>
				</template>
			</Dialog>
			<Dialog title="Deactivate" v-model="showDeactivateDialog">
				<p class="text-base">
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
		</Section>
		<Section
			class="mt-10"
			title="Usage"
			description="Calculated usage of this site updated every hour"
		>
			<SectionCard v-if="currentPlan">
				<div class="flex px-6 py-4 text-base hover:bg-gray-50">
					<div class="w-1/2">
						<div class="leading-6">
							<span class="font-bold"> {{ totalCPUUsage }} hours </span>
							/ {{ currentPlan.cpu_time_per_day }} hours CPU usage
						</div>
						<div class="text-gray-600">
							Cycle resets in {{ hoursUntilReset }} hours
						</div>
					</div>
				</div>
				<div class="flex px-6 py-4 text-base hover:bg-gray-50">
					<div class="w-1/2">
						<div class="leading-6">
							<span class="font-bold"> {{ formatBytes(totalDatabaseUsage, 0, 2) }}</span>
							/ {{ formatBytes(currentPlan.max_database_usage, 0, 2) }} Database usage
						</div>
						<div class="text-gray-600">
							Available database space: {{ formatBytes(currentPlan.max_database_usage - totalDatabaseUsage, 0, 2) }}
						</div>
					</div>
				</div>
				<div class="flex px-6 py-4 text-base hover:bg-gray-50">
					<div class="w-1/2">
						<div class="leading-6">
							<span class="font-bold"> {{ formatBytes(totalDiskUsage, 0, 2) }}</span>
							/ {{ formatBytes(currentPlan.max_storage_usage, 0, 2) }} Disk usage
						</div>
						<div class="text-gray-600">
							Available Storage space: {{ formatBytes(currentPlan.max_storage_usage - totalDiskUsage, 0, 2) }}
						</div>
					</div>
				</div>
			</SectionCard>
		</Section>
		<Section
			class="mt-10"
			title="History"
			description="Log of plan changes for this site"
		>
			<SectionCard>
				<div
					class="px-6 py-4 text-base hover:bg-gray-50"
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
					<div class="text-sm text-gray-600">
						<FormatDate>{{ row.timestamp }}</FormatDate>
					</div>
				</div>
			</SectionCard>
		</Section>
	</div>
</template>

<script>
import SitePlansTable from '@/views/partials/SitePlansTable';

export default {
	name: 'SitePlan',
	props: ['site'],
	components: {
		SitePlansTable
	},
	data() {
		return {
			currentPlan: null,
			totalCPUUsage: 0,
			totalDatabaseUsage: 0,
			totalDiskUsage: 0,
			hoursUntilReset: 0,
			history: [],
			showChangePlanDialog: false,
			plans: [],
			selectedPlan: null,
			showDeactivateDialog: false
		};
	},
	resources: {
		changePlan() {
			return {
				method: 'press.api.site.change_plan',
				params: {
					name: this.site.name,
					plan: this.selectedPlan?.name
				},
				onSuccess() {
					this.$notify({
						title: `Plan changed to ${this.selectedPlan.plan_title}`,
						icon: 'check',
						color: 'green'
					});
					this.showChangePlanDialog = false;
					this.selectedPlan = null;
					this.fetchCurrentPlan();
					this.fetchPlans();
				}
			};
		}
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
			this.totalDatabaseUsage = out.total_database_usage;
			this.totalDiskUsage = out.total_storage_usage;
			this.hoursUntilReset = out.hours_until_reset;
		},
		async fetchPlans() {
			this.plans = await this.$call('press.api.site.get_plans');
			this.plans = this.plans.map(plan => {
				if (this.currentPlan.name === plan.name) {
					plan.disabled = true;
				}

				if (
					this.totalDiskUsage > plan.max_storage_usage ||
					this.totalDatabaseUsage > plan.max_database_usage
				) {
					plan.disabled = true;
				}
				return plan;
			});
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
