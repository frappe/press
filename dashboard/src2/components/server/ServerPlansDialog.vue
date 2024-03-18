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
			<ServerPlansCards v-model="plan" :plans="$resources.serverPlans.data" />
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
			plan: null
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
