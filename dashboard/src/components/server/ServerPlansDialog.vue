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
					disabled: !plan || plan === $server?.doc.plan,
				},
			],
		}"
		v-model="show"
	>
		<template #body-content>
			<!-- Don't show premium plans for Hetzner & DigitalOcean -->
			<div
				class="mb-4 mt-2 w-full space-y-2"
				v-if="
					this.$server?.doc?.provider != 'Hetzner' &&
					this.$server?.doc?.provider != 'DigitalOcean'
				"
			>
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

			<!-- CPU and Ram only upgrade choice -->
			<div
				v-if="
					this.$server?.doc?.provider === 'Hetzner' ||
					this.$server?.doc?.provider === 'DigitalOcean'
				"
				class="flex flex-col overflow-hidden rounded text-left w-full p-3 mb-4 cursor-pointer gap-3"
				:class="{
					'border-amber-300 bg-amber-100 border-2': !cpu_and_memory_only_resize,
					'border-blue-300 bg-blue-100 border-2': cpu_and_memory_only_resize,
				}"
				@click.prevent="
					cpu_and_memory_only_resize = !cpu_and_memory_only_resize
				"
			>
				<Checkbox
					class="cursor-pointer"
					size="sm"
					v-model="cpu_and_memory_only_resize"
					label="CPU and Memory only resize"
				/>

				<p class="text-base leading-relaxed" v-if="!cpu_and_memory_only_resize">
					<b>Note :</b> You won't be able to downgrade this server to a plan
					with a smaller disk size.<br />
					If you only want to upgrade CPU and memory without changing the disk
					size, keep this option checked.
				</p>
				<p v-else class="text-base leading-relaxed">
					To view plans that include disk upgrades, uncheck this option.
				</p>
			</div>

			<div
				class="h-64 flex flex-row justify-center items-center gap-2"
				v-if="$resources?.serverPlansdata?.loading"
			>
				<Spinner class="w-4" /> Loading Server Plans...
			</div>
			<div v-else>
				<!-- Server Plan Type Selection -->
				<div
					class="w-full space-y-2 mb-4"
					v-if="Object.keys(serverPlanTypes).length > 1"
				>
					<div class="grid grid-cols-2 gap-3">
						<button
							v-for="planType in Object.values(serverPlanTypes).sort(
								(a, b) => a.order_in_list - b.order_in_list,
							)"
							:key="planType.name"
							@click="serverPlanType = planType.name"
							:class="[
								serverPlanType === planType.name
									? 'border-gray-900 ring-1 ring-gray-900'
									: 'border-gray-300',
								'flex w-full flex-col overflow-hidden rounded border text-left hover:bg-gray-50',
							]"
						>
							<div class="w-full p-3">
								<div class="flex items-center justify-between">
									<div class="flex w-full items-center">
										<span class="truncate text-lg font-medium text-gray-900">
											{{ planType.title }}
										</span>
									</div>
								</div>
								<div
									class="mt-1 text-sm text-gray-600"
									v-if="planType.description"
								>
									{{ planType.description }}
								</div>
							</div>
						</button>
					</div>
				</div>

				<!-- Single Plan Type Message -->
				<div
					v-else-if="Object.keys(serverPlanTypes).length === 1"
					class="flex flex-col rounded border border-gray-300 p-3 gap-2 mb-4"
				>
					<p class="text-base text-gray-900">
						<span class="font-medium">{{
							Object.values(serverPlanTypes)[0].title
						}}</span>
						machines are available.
					</p>

					<p class="text-base text-gray-600">
						{{ Object.values(serverPlanTypes)[0].description }}
					</p>
				</div>

				<!-- Site Plans Cards -->
				<ServerPlansCards v-model="plan" :plans="filteredServerPlans" />
			</div>
			<ErrorMessage class="mt-2" :message="$server.changePlan.error" />
		</template>
	</Dialog>
</template>
<script>
import { getCachedDocumentResource, Checkbox, Spinner } from 'frappe-ui';
import ServerPlansCards from './ServerPlansCards.vue';

export default {
	components: { ServerPlansCards, Checkbox, Spinner },
	props: {
		server: {
			type: String,
			required: true,
		},
		serverType: {
			type: String,
			required: true,
		},
	},
	data() {
		return {
			show: true,
			plan: null,
			planType: 'Standard',
			serverPlanType: '',
			cpu_and_memory_only_resize: true,
		};
	},
	watch: {
		server: {
			immediate: true,
			handler(serverName) {
				if (serverName) {
					if (this.$server?.doc?.plan) {
						this.plan = this.$server.doc.current_plan;
						this.serverPlanType = this.$server.doc.current_plan.plan_type;
					}
				}
			},
		},
		cpu_and_memory_only_resize(value) {
			if (!this.$resources?.serverPlansdata) return;
			this.$resources?.serverPlansdata.submit();
		},
	},
	resources: {
		serverPlansdata() {
			return {
				url: 'press.api.server.plans',
				params: {
					name: this.cleanedServerType,
					cluster: this.$server.doc.cluster,
					platform: this.$server.doc.current_plan.platform,
					resource_name: this.$server.doc.name,
					cpu_and_memory_only_resize: this.cpu_and_memory_only_resize,
				},
				auto: true,
				initialData: {
					plans: [],
					types: {},
				},
			};
		},
	},
	methods: {
		changePlan() {
			// TODO: Add confirmation dialog for hetzner plan upgrade

			return this.$server.changePlan.submit(
				{
					plan: this.plan.name,
					upgrade_disk: !this.cpu_and_memory_only_resize,
				},
				{
					onSuccess: () => {
						this.show = false;

						const plan = this.serverPlans.find(
							(plan) => plan.name === this.$server.doc.plan,
						);

						const formattedPlan = plan
							? `${this.$format.planTitle(plan)}/mo`
							: this.$server.doc.plan;

						this.$toast.success(`Plan changed to ${formattedPlan}`);
					},
				},
			);
		},
	},
	computed: {
		$server() {
			return getCachedDocumentResource(this.cleanedServerType, this.server);
		},
		serverPlans() {
			return this.$resources.serverPlansdata?.data?.plans || [];
		},
		serverPlanTypes() {
			// Find out the plan_types that we have
			let filtered_types = {};
			this.serverPlans.forEach((plan) => {
				filtered_types[plan.plan_type] =
					this.$resources.serverPlansdata?.data?.types[plan.plan_type];
			});
			return filtered_types;
		},
		cleanedServerType() {
			return this.serverType === 'Replication Server'
				? 'Database Server'
				: this.serverType;
		},
		filteredServerPlans() {
			let plans = [];
			if (this.planType == 'Premium') {
				plans = this.serverPlans.filter((p) => p.premium === 1);
			} else {
				plans = this.serverPlans.filter((p) => p.premium === 0);
			}
			return plans.filter((plan) => plan.plan_type === this.serverPlanType);
		},
	},
};
</script>
