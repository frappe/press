<template>
	<div class="space-y-6">
		<div class="text-base text-gray-800">
			<div>Not sure? Start with the smallest plan and upgrade anytime. Billing is prorated.</div>
		</div>
		<div class="@container space-y-4" v-if="hasPlans">
			<div
				v-for="(group, groupIndex) in displayGroups"
				:key="group.label || groupIndex"
				class="rounded-lg bg-gray-50 p-4"
			>
				<div class="grid gap-4 @[38rem]:grid-cols-[180px_minmax(0,1fr)]">
					<div>
						<div v-if="group.label" class="text-lg font-semibold text-gray-900">
							{{ group.label }}
						</div>
						<div v-if="group.description" class="mt-1 text-p-sm text-gray-700">
							{{ group.description }}
						</div>
						<div
							v-if="group.commonFeatures && group.commonFeatures.length"
							class="mt-3 space-y-3 text-sm text-gray-700"
						>
							<Tooltip
								v-for="(feature, featureIndex) in group.commonFeatures"
								:key="`${group.label}-common-${featureIndex}`"
								:text="feature.tooltip || ''"
								:disabled="!feature.tooltip"
								:hoverDelay="0.1"
								placement="top"
							>
								<div class="flex items-center gap-2">
									<component
										:is="_icon(feature.icon || 'circle', 'size-3.5 text-gray-600')"
									/>
									<span>{{ feature.label }}</span>
								</div>
							</Tooltip>
						</div>
					</div>
					<div class="space-y-2">
						<button
							v-for="plan in group.plans"
							:key="plan.name"
							class="flex w-full items-center justify-between gap-4 rounded-md border bg-white p-3 text-left hover:ring-1 hover:ring-gray-700 focus:outline-none focus-visible:ring focus-visible:ring-outline-gray-3"
							:class="[
								currentPlan?.name === plan?.name
									? 'border-gray-900 ring-1 ring-gray-900'
									: 'border-gray-300',
								{
									'pointer-events-none opacity-50': plan?.disabled,
								},
							]"
							@click="$emit('update:modelValue', plan)"
						>
								<div class="min-w-0">
									<div class="flex items-baseline gap-2">
										<Tooltip
											:text="$format.userCurrency($format.pricePerDay($team.doc.currency === 'INR' ? plan.price_inr : plan.price_usd)) + '/day'"
											:disabled="!(plan.price_inr || plan.price_usd)"
										>
											<span class="text-base whitespace-nowrap font-semibold text-gray-900">
												<template v-if="plan.label">{{ plan.label }}</template>
												<template v-else>
													{{ plan.displayTitle }}
													<span v-if="plan.displayUnit" class="text-gray-700">
														{{ plan.displayUnit }}
													</span>
												</template>
											</span>
										</Tooltip>
									</div>
								</div>
								<div
									class="grid items-center gap-4 text-sm text-gray-800"
									style="grid-template-columns: repeat(3, minmax(100px, 1fr))"
								>
									<Tooltip
										v-for="(item, itemIndex) in getAllPlanItems(plan, group)"
										:key="`${plan.name}-item-${itemIndex}`"
										:disabled="!item?.tooltip"
										:text="item.tooltip"
										placement="top"
										:hover-delay="0"
									>
										<div class="flex items-center gap-2">
											<component
												:is="_icon(item.icon || 'circle', 'size-3.5 text-gray-600')"
											/>
											<span>{{ item.label }}</span>
										</div>
									</Tooltip>
								</div>
						</button>
					</div>
				</div>
			</div>
		</div>
		<div v-else class="flex h-6 items-center">
			<div class="text-base text-gray-600">No plans available</div>
		</div>
	</div>
</template>

<script>
import { Tooltip } from 'frappe-ui';
import { getPlans } from '../data/plans';
import { icon } from '../utils/components';

export default {
	name: 'SitePlansCards',
	props: {
		modelValue: {
			type: Object,
			default: null,
		},
		isPrivateBenchSite: {
			type: Boolean,
			default: false,
		},
		isDedicatedServerSite: {
			type: Boolean,
			default: false,
		},
		selectedCluster: {
			type: String,
			default: null,
		},
		selectedApps: {
			type: Array,
			default: null,
		},
		selectedVersion: {
			type: String,
			default: null,
		},
		selectedProvider: {
			type: String,
			default: null,
		},
		hideRestrictedPlans: {
			type: Boolean,
			default: false,
		},
	},
	emits: ['update:modelValue'],
	components: {
		Tooltip,
	},
	computed: {
		currentPlan: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			},
		},
		basePlans() {
			let plans = getPlans();

			if (this.isPrivateBenchSite) {
				plans = plans.filter((plan) => plan.private_benches);
			}
			if (this.isPrivateBenchSite && this.isDedicatedServerSite) {
				plans = plans.filter((plan) => plan.dedicated_server_plan);
			} else {
				plans = plans.filter((plan) => !plan.dedicated_server_plan);
			}
			if (this.selectedCluster) {
				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.clusters.length == 0
								? false
								: !plan.clusters.includes(this.selectedCluster)),
					};
				});
			}
			if (this.selectedApps) {
				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.allowed_apps.length == 0
								? false
								: !this.selectedApps.every((app) =>
										plan.allowed_apps.includes(app.app),
									)),
					};
				});
			}
			if (this.selectedVersion) {
				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.bench_versions.length == 0
								? false
								: !plan.bench_versions.includes(this.selectedVersion)),
					};
				});
			}
			if (this.hideRestrictedPlans) {
				plans = plans.filter((plan) => !plan.restricted_plan);
			}
			if (this.selectedProvider) {
				const provider = ["Generic", "Scaleway"].includes(
					this.selectedProvider,
				)
					? "AWS EC2"
					: this.selectedProvider;

				plans = plans.map((plan) => {
					return {
						...plan,
						disabled:
							plan.disabled ||
							(plan.cloud_providers && plan.cloud_providers.length > 0
								? !plan.cloud_providers.includes(provider)
								: false),
					};
				});
			}

			plans = plans.filter((plan) => !plan.disabled);

			return plans.map((plan) => {
				const computeTier = this.getComputeTier(plan);
				return {
					...plan,
					computeTier,
					features: [
						{
							label: 'Compute',
							display: `${plan.cpu_time_per_day} ${this.$format.plural(plan.cpu_time_per_day, 'hr', 'hrs')}/day`,
							condition: !plan.name.includes('Unlimited'),
							value: plan.cpu_time_per_day,
							tooltip: 'Amount of compute allocated per day',
							icon: 'cpu',
							scope: 'plan',
						},
						{
							label: 'Database',
							condition: !plan.name.includes('Unlimited'),
							value: this.$format.bytes(plan.max_database_usage, 1, 2).replace(/\s/g, ''),
							tooltip: 'Maximum database storage allowed',
							icon: 'database',
							scope: 'plan',
						},
						{
							label: 'Disk',
							condition: !plan.name.includes('Unlimited'),
							value: this.$format.bytes(plan.max_storage_usage, 1, 2).replace(/\s/g, ''),
							tooltip: 'Maximum disk storage allowed',
							icon: 'hard-drive',
							scope: 'plan',
						},
						{
							key: 'support_included',
							value: plan.support_included ? 'Product Support' : '',
							icon: 'shield',
						},
						{
							key: 'database_access',
							value: plan.database_access ? 'Database Access' : '',
							icon: 'key',
						},
						{
							key: 'offsite_backups',
							value: plan.offsite_backups ? 'Offsite Backups' : '',
							icon: 'cloud',
						},
						{
							key: 'monitor_access',
							value: plan.monitor_access ? 'Advanced Monitoring' : '',
							icon: 'activity',
						},
						{
							value: plan.name.includes('Unlimited - Low')
								? 'Allocate fewer resources here (more for other benches)'
								: '',
							icon: 'info',
							scope: 'plan',
						},
					].filter((feature) => feature.condition ?? true),
				};
			});
		},
		planGroups() {
			const tiers = [
				{
					key: 'low',
					label: 'Starter',
					description: 'Ideal for small workloads with light usage',
				},
				{
					key: 'medium',
					label: 'Growth',
					description: 'Ideal for medium workloads with growing usage',
				},
				{
					key: 'high',
					label: 'Enterprise',
					description: 'Ideal for heavy workloads with large data',
				},
			];
			const alwaysCommonFeatures = [
				{
					key: 'unlimited_users',
					label: 'Unlimited Users',
					icon: 'users',
					tooltip: 'Unlimited users included with every plan.',
				},
			];
			const commonFeatureDefs = [
				{
					key: 'support_included',
					label: 'Product Support',
					icon: 'shield',
					tooltip: 'Includes product support from the Frappe team.',
				},
				{
					key: 'database_access',
					label: 'Database Access',
					icon: 'key',
					tooltip: 'Direct database access for advanced queries and tooling.',
				},
				{
					key: 'offsite_backups',
					label: 'Offsite Backups',
					icon: 'cloud',
					tooltip: 'Includes automated offsite backups.',
				},
				{
					key: 'monitor_access',
					label: 'Advanced Monitoring',
					icon: 'activity',
					tooltip: 'Includes advanced monitoring access.',
				},
			];

			return tiers
				.map((tier) => {
					const tierPlans = this.basePlans.filter(
						(plan) => plan.computeTier === tier.key,
					);
					const commonFeatures = [
						...alwaysCommonFeatures,
						...commonFeatureDefs.filter((feature) =>
							tierPlans.every((plan) => plan[feature.key]),
						),
					];
					return {
						label: tier.label,
						description: tier.description,
						plans: tierPlans,
						commonFeatures,
						commonFeatureKeys: commonFeatures.map((feature) => feature.key),
					};
				})
				.filter((group) => group.plans.length);
		},
		displayGroups() {
			return this.planGroups.map((group) => {
				return {
					...group,
					plans: group.plans.map((plan) => {
										const display = this.$format.planDisplay(plan, false);
						return {
							...plan,
							displayTitle: display.title,
							displayUnit: display.unit,
						};
					}),
				};
			});
		},
		hasPlans() {
			return this.displayGroups.length > 0;
		},
	},
	methods: {
		_icon(iconName, classes) {
			return icon(iconName, classes);
		},
		getAllPlanItems(plan, group) {
			const items = [];
			const commonKeys = group?.commonFeatureKeys || [];

			if (plan.features) {
				plan.features.forEach((feature) => {
					if (feature.value && !commonKeys.includes(feature.key)) {
						items.push({
							icon: feature.icon,
							label: feature.display || feature.value,
							sublabel: feature.label || null,
							tooltip: feature.tooltip || null,
						});
					}
				});
			}

			return items;
		},
		getComputeTier(plan) {
			const compute = plan.cpu_time_per_day ?? 0;
			if (compute === 0) {
				// Unlimited compute plans
				return 'high';
			}
			if (compute >= 4) {
				return 'high';
			}
			if (compute >= 2) {
				return 'medium';
			}
			return 'low';
		},

	},
};
</script>
