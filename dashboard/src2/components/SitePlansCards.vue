<template>
	<div class="@container" v-if="plans.length">
		<!-- TODO: make Tabs more flexible in terms of styling -->
		<FTabs class="-ml-[19px]" :tabs="tabs" v-model="currentTab">
			<template v-slot="{ tab }">
				<div class="grid grid-cols-2 gap-3 p-5 @4xl:grid-cols-4">
					<button
						v-for="(plan, i) in tab.plans"
						:key="plan.name"
						class="flex flex-col overflow-hidden rounded border text-left hover:bg-gray-50"
						:class="[
							modelValue === plan.name
								? 'border-gray-900 ring-1 ring-gray-900'
								: 'border-gray-300',
							{
								'pointer-events-none': plan.disabled
							}
						]"
						@click="$emit('update:modelValue', plan.name)"
					>
						<div
							class="w-full border-b p-3"
							:class="[
								modelValue === plan.name
									? 'border-gray-900 ring-1 ring-gray-900'
									: ''
							]"
						>
							<div class="flex items-center justify-between">
								<div class="text-lg">
									<span class="font-medium text-gray-900">
										{{ $format.planTitle(plan) }}
									</span>
									<span class="text-gray-700"> /mo</span>
								</div>

								<Tooltip
									v-if="plan.support_included"
									text="Frappe Product Warranty"
									placement="top"
								>
									<Badge
										class="hover:cursor-pointer"
										color="blue"
										label="Support"
									/>
								</Tooltip>
							</div>
							<div class="mt-1 text-sm text-gray-600">
								{{ $team.doc.country === 'India' ? '₹' : '$'
								}}{{
									$team.doc.country === 'India'
										? plan.price_per_day_inr
										: plan.price_per_day_usd
								}}
								/day
							</div>
						</div>
						<div class="p-3 text-p-sm text-gray-800">
							<div>
								<span class="font-medium">{{ plan.cpu_time_per_day }} </span>
								<span class="ml-1 text-gray-600">
									{{
										$format.plural(
											plan.cpu_time_per_day,
											'compute hour',
											'compute hours'
										)
									}}
									/ day
								</span>
							</div>
							<div>
								<span class="font-medium">
									{{ $format.bytes(plan.max_database_usage, 0, 2) }}
								</span>
								<span class="text-gray-600"> database </span>
							</div>
							<div>
								<span class="font-medium">
									{{ $format.bytes(plan.max_storage_usage, 0, 2) }}
								</span>
								<span class="text-gray-600"> disk </span>
							</div>
						</div>
					</button>
				</div>
			</template>
		</FTabs>
	</div>
</template>

<script>
import { Tabs } from 'frappe-ui';

export default {
	name: 'SitePlansCards',
	props: ['modelValue'],
	emits: ['update:modelValue'],
	components: {
		FTabs: Tabs
	},
	data() {
		return {
			currentTab: 0
		};
	},
	resources: {
		plans() {
			return {
				url: 'press.api.site.get_plans',
				cache: 'site.plans',
				auto: true
			};
		}
	},
	computed: {
		tabs() {
			return ['Basic', 'Support Included'].map(label => {
				let plans = this.plans.filter(p =>
					label === 'Support Included'
						? p.support_included
						: !p.support_included
				);
				return {
					label,
					plans
				};
			});
		},
		plans() {
			return this.$resources.plans.data || [];
		}
	}
};
</script>
