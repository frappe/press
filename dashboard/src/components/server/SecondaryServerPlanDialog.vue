<template>
	<Dialog
		:options="{
			title: 'Select Secondary Application Server Plan',
			size: '5xl',
			actions: [
				{
					label: 'Setup Secondary Server',
					variant: 'solid',
					onClick: setupSecondaryServer,
					disabled: !$resources.secondaryServerPlans.data?.length,
				},
			],
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="mb-4 mt-2 w-full space-y-2">
				<div class="grid grid-cols-2 gap-3">
					<button
						v-for="c in [
							{
								name: 'Standard',
								description: 'Includes standard support and SLAs',
							},
							{
								name: 'Premium',
								description: 'Includes enterprise support and SLAs',
							},
						]"
						:key="c.name"
						@click="planType = c.name"
						:class="[
							planType === c.name
								? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
								: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
							'flex w-full items-center rounded border p-3 text-left text-base text-gray-900',
						]"
					>
						<div class="flex w-full items-center justify-between space-x-2">
							<span class="text-sm font-medium">
								{{ c.name }}
							</span>
							<Tooltip :text="c.description">
								<lucide-info class="h-4 w-4 text-gray-500" />
							</Tooltip>
						</div>
					</button>
				</div>
			</div>
			<ServerPlansCards
				v-model="plan"
				:plans="
					planType === 'Premium'
						? $resources.secondaryServerPlans.data.filter(
								(p) => p.premium === 1,
							)
						: $resources.secondaryServerPlans.data.filter(
								(p) => p.premium === 0,
							)
				"
				:hourly-pricing="true"
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
			required: true,
		},
	},
	data() {
		return {
			show: true,
			plan: null,
			planType: 'Standard',
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
			},
		},
	},
	resources: {
		secondaryServerPlans() {
			return {
				url: 'press.api.server.secondary_server_plans',
				params: {
					name: 'Server',
					cluster: this.$server.doc.cluster,
					platform: this.$server.doc.current_plan.platform,
					current_plan: this.$server.doc.current_plan.name,
				},
				auto: true,
				initialData: [],
			};
		},
	},
	methods: {
		setupSecondaryServer() {
			return this.$server.setupSecondaryServer.submit(
				{ server_plan: this.plan.name },
				{
					onSuccess: () => {
						this.show = false;
						this.$toast.success('Starting secondary server setup');
						this.$router.push({
							path: this.$server.doc.name,
							path: 'plays',
						});
					},
				},
			);
		},
	},
	computed: {
		$server() {
			return getCachedDocumentResource('Server', this.server);
		},
	},
};
</script>
