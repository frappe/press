<template>
	<div class="space-y-6">
		<!-- Step 1 : Choose a plan -->
		<div>
			<div v-if="step == 1">
				<div class="flex items-center space-x-2">
					<TextInsideCircle>1</TextInsideCircle>
					<span class="text-base font-medium"> Choose Site Plan </span>
				</div>
				<div class="pl-7">
					<SitePlansCards
						:saas="true"
						:hideRestrictedPlans="true"
						v-model="selectedPlan"
						class="mt-4"
					/>
					<p></p>
					<div class="flex w-full justify-end">
						<Button
							class="mt-2 w-full sm:w-fit"
							variant="solid"
							@click="confirmPlan"
						>
							Confirm Plan
						</Button>
					</div>
				</div>
			</div>
			<div v-else>
				<div class="flex items-center justify-between space-x-2">
					<div class="flex items-center space-x-2">
						<TextInsideCircle>1</TextInsideCircle>
						<span class="text-base font-medium">
							<!-- Site plan selected ({{ selectedPlan.name }}) -->
						</span>
					</div>
					<div
						class="grid h-4 w-4 place-items-center rounded-full bg-green-500/90"
					>
						<i-lucide-check class="h-3 w-3 text-white" />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { defineAsyncComponent } from 'vue';
import { setConfig, frappeRequest } from 'frappe-ui';

export default {
	name: 'In-Desk Checkout',
	components: {
		SitePlansCards: defineAsyncComponent(() =>
			import('../../components/SitePlansCards.vue')
		),
		TextInsideCircle: defineAsyncComponent(() =>
			import('../../components/TextInsideCircle.vue')
		)
	},
	beforeMount() {
		let request = options => {
			let _options = options || {};
			_options.headers = options.headers || {};
			_options.headers['x-site-access-token'] = this.$route.params.accessToken;
			return frappeRequest(_options);
		};
		setConfig('resourceFetcher', request);
	},
	data() {
		return {
			selectedPlan: {
				name: ''
			},
			step: 1
		};
	},
	methods: {
		confirmPlan() {
			if (!this.selectedPlan) {
				toast.error('Please select a plan');
				return;
			}
			this.step = 2;
		}
	}
};
</script>
