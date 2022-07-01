<script setup>
import { ref, reactive } from 'vue';
import useResource from '@/composables/resource';
import AppPlanCard from '@/components/AppPlanCard.vue';
import PrinterIcon from '../components/PrinterIcon.vue';

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
		refreshState();
	}
});

const createAppPlan = useResource({
	method: 'press.api.marketplace.create_app_plan',
	validate() {
		if (!currentEditingPlan.plan_title) {
			return 'Plan name is required';
		}
	},
	onSuccess() {
		refreshState();
	}
});

function editPlan(plan) {
	if (plan) {
		Object.assign(currentEditingPlan, plan);
		currentEditingPlan.features = Array.from(plan.features); // Non-reference copy
	}
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
		createAppPlan.submit({
			plan_data: currentEditingPlan,
			marketplace_app: props.app?.name
		});
	}
}

function refreshState() {
	appPlans.fetch();
	showEditPlanDialog.value = false;
	resetCurrentEditingPlan();
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

				<div v-else-if="appPlans.data">
					<div
						v-if="appPlans.data.length > 0"
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
					<div v-else>
						<div class="mt-7 flex flex-col items-center justify-center">
							<PrinterIcon class="mb-5 h-20 w-20" />
							<p class="mb-1 text-2xl font-semibold text-gray-900">
								Create a plan
							</p>
							<p class="mb-3.5 text-base text-gray-700">
								Looks like you haven't created any plans yet
							</p>
							<Button type="primary" @click="editPlan()">Create plan</Button>
						</div>
					</div>
				</div>
			</div>
		</Card>

		<Dialog v-model="showEditPlanDialog" title="Edit Plan">
			<div>
				<div class="mb-4">
					<Input
						placeholder="My Pro Plan"
						type="text"
						label="Name"
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
