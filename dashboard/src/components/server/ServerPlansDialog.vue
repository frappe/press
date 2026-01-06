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
			<!-- Don't show premium plans for Hetzner provider -->
			<div
				class="mb-4 mt-2 w-full space-y-2"
				v-if="this.$server?.doc?.provider != 'Hetzner'"
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
				v-if="this.$server?.doc?.provider === 'Hetzner'"
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

			<!-- Site Plans Cards -->
			<div
				class="h-64 flex flex-row justify-center items-center gap-2"
				v-if="$resources?.serverPlans?.loading"
			>
				<Spinner class="w-4" /> Loading Server Plans...
			</div>
			<ServerPlansCards
				v-else
				v-model="plan"
				:plans="
					planType === 'Premium'
						? $resources.serverPlans.data.filter((p) => p.premium === 1)
						: $resources.serverPlans.data.filter((p) => p.premium === 0)
				"
			/>
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
					}
				}
			},
		},
		cpu_and_memory_only_resize(value) {
			if (!this.$resources?.serverPlans) return;
			this.$resources?.serverPlans.submit();
		},
	},
	resources: {
		serverPlans() {
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
				initialData: [],
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

						const plan = this.$resources.serverPlans.data.find(
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
		cleanedServerType() {
			return this.serverType === 'Replication Server'
				? 'Database Server'
				: this.serverType;
		},
	},
};
</script>
