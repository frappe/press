<template>
	<Dialog
		:options="{
			title: 'Change Plan',
			size: '5xl',
			actions: [
				{
					label: 'Change plan',
					variant: 'solid',
					onClick: changePlan,
					disabled: !plan || plan === $server?.doc.plan
				}
			]
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="mt-2 mb-4 w-full space-y-2">
				<div class="grid grid-cols-2 gap-3">
					<button
						v-for="c in [
							{
								name: 'Standard',
								description: 'Includes standard support and SLAs'
							},
							{
								name: 'Premium',
								description: 'Includes enterprise support and SLAs'
							}
						]"
						:key="c.name"
						@click="planType = c.name"
						:class="[
							planType === c.name
								? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
								: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
							'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
						]"
					>
						<div class="flex w-full items-center justify-between space-x-2">
							<span class="text-sm font-medium">
								{{ c.name }}
							</span>
							<Tooltip :text="c.description">
								<i-lucide-info class="h-4 w-4 text-gray-500" />
							</Tooltip>
						</div>
					</button>
				</div>
			</div>
			<ServerPlansCards
				v-model="plan"
				:plans="
					planType === 'Premium'
						? $resources.serverPlans.data.filter(p => p.premium === 1)
						: $resources.serverPlans.data.filter(p => p.premium === 0)
				"
			/>
			<ErrorMessage class="mt-2" :message="$server.changePlan.error" />
		</template>
	</Dialog>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import ServerPlansCards from './ServerPlansCards.vue';

export default {
	components: { ServerPlansCards },
	props: {
		server: {
			type: String,
			required: true
		},
		serverType: {
			type: String,
			required: true
		}
	},
	data() {
		return {
			show: true,
			plan: null,
			planType: 'Standard'
		};
	},
	watch: {
		server: {
			immediate: true,
			handler(serverName) {
				if (serverName) {
					if (this.$server?.doc?.plan) {
						this.plan = this.$server.doc.current_plan;
					}
				}
			}
		}
	},
	resources: {
		serverPlans() {
			return {
				url: 'press.api.server.plans',
				params: {
					name: this.serverType,
					cluster: this.$server.doc.cluster
				},
				auto: true,
				initialData: []
			};
		}
	},
	methods: {
		changePlan() {
			return this.$server.changePlan.submit(
				{ plan: this.plan.name },
				{
					onSuccess: () => {
						this.show = false;
						let plan = (serverPlans.data || []).find(
							plan => plan.name === this.$server.doc.plan
						);
						let formattedPlan = plan
							? `${this.$format.planTitle(plan)}/mo`
							: this.$server.doc.plan;
						this.$toast.success(`Plan changed to ${formattedPlan}`);
					}
				}
			);
		}
	},
	computed: {
		$server() {
			return getCachedDocumentResource(this.serverType, this.server);
		}
	}
};
</script>
