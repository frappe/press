<template>
	<SiteAppPlanSelectorDialog
		v-model="showDialog"
		:app="app"
		:currentPlan="currentPlan"
		@plan-select="onPlanSelect"
	/>
</template>

<script>
import SiteAppPlanSelectorDialog from './SiteAppPlanSelectorDialog.vue';
import { toast } from 'vue-sonner';

export default {
	components: {
		SiteAppPlanSelectorDialog
	},
	props: ['app', 'currentPlan'],
	emits: ['plan-changed'],
	data() {
		return {
			showDialog: true
		};
	},
	resources: {
		changeAppPlan: {
			url: 'press.api.marketplace.change_app_plan'
		}
	},
	methods: {
		onPlanSelect(plan) {
			toast.promise(
				this.$resources.changeAppPlan.submit({
					subscription: this.app.subscription.name,
					new_plan: plan.name
				}),
				{
					loading: 'Changing plan...',
					success: () => {
						this.$emit('plan-changed', plan);
						return 'Plan changed successfully';
					},
					error: e => {
						return e.messages.length ? e.messages.join('\n') : e.message;
					}
				}
			);
		}
	}
};
</script>
