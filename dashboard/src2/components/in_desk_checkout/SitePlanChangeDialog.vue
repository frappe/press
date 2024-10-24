<template>
	<Dialog
		:options="{
			title: 'Change Plan',
			size: '3xl',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					loading: this.$resources.changePlan.loading,
					onClick: () => this.changePlan()
				}
			]
		}"
	>
		<template v-slot:body-content>
			<SitePlansCards
				v-if="teamCurrency"
				:teamCurrency="teamCurrency"
				v-model="selectedPlan"
				class="mt-4"
			/>
			<div class="mt-3 text-xs text-gray-700">
				<p>
					* <strong>Support</strong> includes only issues and bug fixes related
					to Frappe apps, functional queries will not be entertained.
				</p>
				<p class="mt-1">
					** If you face any issue while using Frappe Cloud, you can raise
					support ticket regardless of site plan.
				</p>
			</div>
			<ErrorMessage class="mt-4" :message="$resources.changePlan.error" />
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'SitePlanChangeDialog',
	inject: ['team', 'site'],
	components: {
		SitePlansCards: defineAsyncComponent(() => import('./SitePlanCards.vue'))
	},
	data() {
		return {
			selectedPlan: null,
			validationMessage: null
		};
	},
	mounted() {
		if (this.site?.data?.plan?.name) {
			this.selectedPlan = this.site?.data?.plan;
		}
	},
	resources: {
		changePlan() {
			return {
				url: 'press.saas.api.site.change_plan',
				params: {
					plan: this.selectedPlan?.name
				},
				onSuccess() {
					toast.success(`Plan changed to ${this.selectedPlan.plan_title}`);
					this.showChangePlanDialog = false;
					this.site.reload();
				}
			};
		}
	},
	computed: {
		teamCurrency() {
			return this.team?.data?.currency || 'INR';
		},
		showChangePlanDialog: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		}
	},
	methods: {
		changePlan() {
			if (this.selectedPlan?.name == this.site?.data?.plan?.name) {
				toast.error('Please choose a different plan');
				return;
			}
			this.$resources.changePlan.submit();
		}
	}
};
</script>
