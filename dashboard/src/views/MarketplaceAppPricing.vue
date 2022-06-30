<script setup>
import { ref, reactive } from 'vue';
import useResource from '@/composables/resource';
import AppPlanCard from '@/components/AppPlanCard.vue';

const showEditPlanDialog = ref(false);
const currentEditingPlan = reactive({
	price_inr: 0,
	price_usd: 0,
	features: [''],
	plan_title: ''
});

const props = defineProps({
	app: Object
});

const appPlans = useResource({
	method: 'press.api.marketplace.get_app_plans',
	params: {
		app: props.app?.name
	},
	auto: true
});

const updateAppPlan = useResource({
	method: 'press.api.marketplace.update_app_plan',
	onSuccess() {
		resetCurrentEditingPlan();
		appPlans.fetch();
		showEditPlanDialog.value = false;
	}
});

const createAppPlan = useResource({
	method: 'press.api.marketplace.create_app_plan'
});

function editPlan(plan) {
	Object.assign(currentEditingPlan, plan);
	currentEditingPlan.features = Array.from(plan.features); // Non-reference copy
	showEditPlanDialog.value = true;
}

function addFeatureInput() {
	currentEditingPlan.features.push('');
}

function deleteFeatureInput(idx) {
	currentEditingPlan.features.splice(idx, 1);
}

function savePlan() {
	if (currentEditingPlan.name) {
		updateAppPlan.submit({
			app_plan_name: currentEditingPlan.name,
			updated_plan_data: currentEditingPlan
		});
	} else {
		// If no name ==> Creating a new plan
	}
}

function resetCurrentEditingPlan() {
	Object.assign(currentEditingPlan, {
		price_inr: 0,
		price_usd: 0,
		features: [''],
		plan_title: ''
	});

	updateAppPlan.error = null;
	createAppPlan.error = null;
}
</script>

<template>
	<div>
		<Card title="Pricing Plans" subtitle="Set up pricing plans for this app">
			<div class="mb-4">
				<div v-if="appPlans.loading">
					<Button :loading="true">Loading</Button>
				</div>
				<div
					v-else-if="appPlans.data"
					class="mx-auto grid grid-cols-1 gap-2 md:grid-cols-3"
				>
					<AppPlanCard
						v-for="plan in appPlans.data"
						:plan="plan"
						:key="plan.name"
						:clickable="false"
						:editable="true"
						@beginEdit="editPlan(plan)"
					/>
				</div>
			</div>
		</Card>

		<Dialog v-model="showEditPlanDialog" title="Edit Plan">
			<div>
				<div class="mb-4">
					<Input
						type="text"
						label="Plan Title"
						v-model="currentEditingPlan.plan_title"
					></Input>
				</div>
				<div class="mb-8">
					<h3 class="mb-4 text-lg font-semibold">Subscription Price</h3>
					<div class="grid grid-cols-2 gap-2">
						<Input
							label="Price INR"
							type="text"
							v-model="currentEditingPlan.price_inr"
						></Input>
						<Input
							label="Price USD"
							type="text"
							v-model="currentEditingPlan.price_usd"
						></Input>
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
								<Input
									class="w-full"
									type="text"
									v-model="currentEditingPlan.features[idx]"
								></Input>
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
						<ErrorMessage class="mt-3" :error="updateAppPlan.error" />
						<ErrorMessage class="mt-3" :error="createAppPlan.error" />
					</div>
				</div>
			</div>
			<template #actions>
				<Button
					type="primary"
					:loading="updateAppPlan.loading || createAppPlan.loading"
					@click="savePlan"
					@close="resetCurrentEditingPlan"
					>Save</Button
				>
			</template>
		</Dialog>
	</div>
</template>
