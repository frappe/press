<template>
	<Dialog :options="{ title: 'Edit Plan' }" v-model="showEditPlanDialog">
		<template v-slot:body-content>
			<div>
				<div class="mb-4">
					<input
						type="checkbox"
						id="enabled-checkbox"
						class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
						v-model="currentEditingPlan.enabled"
					/>
					<label for="enabled-checkbox" class="ml-1 text-sm text-gray-900">
						Enabled
					</label>
				</div>
				<div class="mb-4">
					<FormControl
						placeholder="My Pro Plan"
						label="Name"
						v-model="currentEditingPlan.title"
					></FormControl>
				</div>
				<div class="mb-8">
					<h3 class="mb-4 text-lg font-semibold">Subscription Price</h3>
					<div class="grid grid-cols-2 gap-2">
						<FormControl
							label="Price INR"
							v-model="currentEditingPlan.price_inr"
						></FormControl>
						<FormControl
							label="Price USD"
							v-model="currentEditingPlan.price_usd"
						></FormControl>
					</div>
				</div>
				<div>
					<h3 class="mb-4 text-lg font-semibold">Features</h3>
					<div>
						<div
							v-for="(feature, idx) in currentEditingPlan.features"
							class="mb-3.5 flex w-full items-stretch"
						>
							<div
								class="mr-3 flex h-6 w-6 items-center justify-center rounded-full bg-gray-100 text-xs"
							>
								{{ idx + 1 }}
							</div>

							<div class="w-full">
								<FormControl
									class="w-full"
									v-model="currentEditingPlan.features[idx]"
								></FormControl>
							</div>

							<Button
								v-if="idx > 0"
								class="ml-3 rounded-full"
								icon="x"
								@click="deleteFeatureInput(idx)"
							></Button>
						</div>
					</div>
					<div>
						<Button icon-left="plus" @click="addFeatureInput">Add</Button>
					</div>

					<div>
						<ErrorMessage
							class="mt-3"
							:message="$resources.updateAppPlan.error"
						/>
						<ErrorMessage
							class="mt-3"
							:message="$resources.createAppPlan.error"
						/>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				:loading="
					$resources.updateAppPlan.loading || $resources.createAppPlan.loading
				"
				@click="savePlan"
				@close="resetCurrentEditingPlan"
				>Save</Button
			>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';

export default {
	name: 'PlanDialog',
	props: ['app', 'plan'],
	emits: ['plan-created', 'plan-updated'],
	data() {
		return {
			showEditPlanDialog: true,
			currentEditingPlan: {
				price_inr: 0,
				price_usd: 0,
				features: [''],
				title: '',
				enabled: true
			}
		};
	},
	mounted() {
		if (this.plan) {
			Object.assign(this.currentEditingPlan, this.plan);
			this.currentEditingPlan.enabled = Boolean(this.plan.enabled);
			this.currentEditingPlan.features = Array.from(this.plan.features); // Non-reference copy
		}
	},
	resources: {
		appPlans() {
			return {
				url: 'press.api.marketplace.get_app_plans',
				params: {
					app: this.app,
					include_disabled: true
				},
				auto: true
			};
		},
		updateAppPlan() {
			return {
				url: 'press.api.marketplace.update_app_plan',
				onSuccess() {
					this.refreshState();
				}
			};
		},
		createAppPlan() {
			return {
				url: 'press.api.marketplace.create_app_plan',
				validate() {
					if (!this.currentEditingPlan.title) {
						return 'Plan name is required';
					}
				},
				onSuccess() {
					this.refreshState();
				}
			};
		}
	},
	methods: {
		editPlan() {
			if (this.plan) {
				Object.assign(this.currentEditingPlan, this.plan);
				this.currentEditingPlan.enabled = Boolean(this.plan.enabled);
				this.currentEditingPlan.features = Array.from(this.plan.features); // Non-reference copy
			}
			this.showEditPlanDialog = true;
		},
		addFeatureInput() {
			this.currentEditingPlan.features.push('');
		},
		deleteFeatureInput(idx) {
			this.currentEditingPlan.features.splice(idx, 1);
		},

		savePlan() {
			toast.promise(
				this.currentEditingPlan.name
					? this.$resources.updateAppPlan.submit({
							app_plan_name: this.currentEditingPlan.name,
							updated_plan_data: this.currentEditingPlan
					  })
					: this.$resources.createAppPlan.submit({
							plan_data: this.currentEditingPlan,
							marketplace_app: this.app
					  }),
				{
					loading: 'Saving plan...',
					success: () => {
						this.showEditPlanDialog = false;
						if (this.currentEditingPlan.name) {
							this.$emit('plan-updated', this.currentEditingPlan);
							return 'Plan updated successfully';
						} else {
							this.$emit('plan-created', this.currentEditingPlan);
							return 'Plan created successfully';
						}
					},
					error: e => {
						console.log(e);
						return e.messages.length ? e.messages.join('\n') : e.message;
					}
				}
			);
		},

		refreshState() {
			this.$resources.appPlans.fetch();
			this.showEditPlanDialog = false;
			this.resetCurrentEditingPlan();
		},

		resetCurrentEditingPlan() {
			Object.assign(this.currentEditingPlan, {
				price_inr: 0,
				price_usd: 0,
				features: [''],
				title: '',
				enabled: true
			});

			this.$resources.updateAppPlan.error = null;
			this.$resources.createAppPlan.error = null;
		}
	}
};
</script>
