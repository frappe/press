<script setup>
import FeatureList from '@/components/FeatureList.vue';
import { computed, ref } from 'vue';
import useResource from '@/composables/resource';
import call from '../../controllers/call';

const props = defineProps({ app: Object, appName: String });
let showEditDialog = ref(false);
let showCreateDialog = ref(false);
let currentPlanIndex = ref(0);
let modelText = ref('');

// new plan
let title = ref('');
let site_plan = ref('USD 10');
let features = ref([]);
let price_usd = ref(0);
let price_inr = ref(0);

const plans = useResource({
	method: 'press.api.saas.get_plans',
	auto: true,
	params: {
		name: props.appName
	}
});

let plansData = computed(() => {
	if (plans.data) {
		return plans.data.saas_plans;
	}
	return [];
});

let sitePlans = computed(() => {
	if (plans.data) {
		return plans.data.site_plans;
	}
	return [];
});

let editPlan = async plan => {
	let result = await call('press.api.saas.edit_plan', {
		plan: plan,
		name: props.appName
	});
};

let createPlan = async () => {
	let plan = {
		title: title._value,
		site_plan: site_plan._value,
		features: features._value,
		app: props.app.name,
		usd: price_usd._value,
		inr: price_inr._value
	};
	let result = await call('press.api.saas.create_plan', {
		plan: plan,
		name: props.app.name
	});

	if (result) {
		plans.reload();
		$notify({
			title: 'Plan Changed Successfully!',
			icon: 'check',
			color: 'green'
		});
	}
};

const getFeatureList = features => {
	return features.map(function (f) {
		return f['value'];
	});
};
</script>

<template>
	<div v-if="props.appName">
		<div class="pb-3">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="mb-2 text-xl font-bold">Manage Plans</h1>
					<p>Add, remove or edit plans for {{ app.title }} App.</p>
				</div>
				<Button type="primary" iconLeft="plus" @click="showCreateDialog = true">
					Add Plan
				</Button>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-4 md:grid-cols-3" v-if="plansData">
			<Card
				:title="plan.plan"
				v-for="(plan, index) in plansData"
				:key="plan.name"
			>
				<template #actions>
					<Button
						icon-left="edit"
						@click="
							() => {
								showEditDialog = true;
								currentPlanIndex = index;
							}
						"
					>
						Edit
					</Button>
				</template>
				<FeatureList class="mt-5" :features="getFeatureList(plan.features)" />
			</Card>
		</div>
		<Dialog
			title="Edit Plan"
			v-model="showEditDialog"
			v-if="plansData[currentPlanIndex]"
		>
			<template #actions>
				<Button class="mr-2" @click="showEditDialog = false"> Cancel </Button>

				<Button
					type="primary"
					@click="
						() => {
							editPlan(plansData[currentPlanIndex]);
							showEditDialog = false;
						}
					"
				>
					Save
				</Button>
			</template>
			<h6 class="mt-4 mb-4 text-lg font-semibold">Details</h6>
			<Input
				class="mb-3"
				type="text"
				label="Plan Title"
				v-model="plansData[currentPlanIndex].plan"
			/>
			<Input
				class="mb-3"
				type="select"
				:options="sitePlans"
				label="Site Plan"
				v-model="plansData[currentPlanIndex].site_plan"
			/>

			<h6 class="mt-4 mb-4 text-lg font-semibold">Pricing</h6>
			<div class="grid grid-cols-1 gap-2 md:grid-cols-2">
				<Input
					type="text"
					label="Price in USD"
					v-model="plansData[currentPlanIndex].price_usd"
					required
				/>
				<Input
					type="text"
					label="Price in INR"
					v-model="plansData[currentPlanIndex].price_inr"
					required
				/>
			</div>

			<h6 class="mt-4 mb-4 text-lg font-semibold">Plan Features</h6>
			<ol class="grid grid-cols-1 gap-2 md:grid-cols-2">
				<li
					class="mt-1 flex"
					v-for="(feature, index) in plansData[currentPlanIndex].features"
					:key="index"
				>
					<div
						class="mx-2 flex w-7 items-center justify-center rounded-full bg-gray-200 text-sm text-gray-700"
					>
						{{ index + 1 }}
					</div>
					<Input type="text" v-model="feature.value" :key="feature" />
					<div
						class="mx-1 mt-1"
						v-on:click="
							() => {
								plansData[currentPlanIndex].features.splice(index, 1);
							}
						"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="red"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
							class="feather feather-trash-2 mr-2 h-5 w-5"
						>
							<polyline points="3 6 5 6 21 6"></polyline>
							<path
								d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
							></path>
							<line x1="10" y1="11" x2="10" y2="17"></line>
							<line x1="14" y1="11" x2="14" y2="17"></line>
						</svg>
					</div>
				</li>
			</ol>
			<hr class="my-4" />
			<Input class="my-1" type="text" v-model="modelText" />
			<Button
				@click="
					() => {
						plansData[currentPlanIndex].features.push({
							idx: index + 1,
							value: modelText
						});
						modelText = '';
					}
				"
				type="secondary"
				>Add</Button
			>
		</Dialog>
		<Dialog title="Create New Plan" v-model="showCreateDialog" v-if="plansData">
			<template #actions>
				<Button class="mr-2" @click="() => (showCreateDialog = false)">
					Cancel
				</Button>

				<Button
					type="primary"
					@click="
						() => {
							createPlan();
							showCreateDialog = false;
						}
					"
				>
					Save
				</Button>
			</template>
			<h6 class="mt-4 mb-4 text-lg font-semibold">Details</h6>
			<Input
				class="mb-3"
				type="text"
				label="Plan Title"
				v-model="title"
				required
			/>
			<Input
				class="mb-2"
				type="select"
				:options="sitePlans"
				label="Site Plan"
				v-model="site_plan"
				required
			/>
			<h6 class="mt-4 mb-4 text-lg font-semibold">Pricing</h6>
			<div class="grid grid-cols-1 gap-2 md:grid-cols-2">
				<Input type="text" label="Price in USD" v-model="price_usd" required />
				<Input type="text" label="Price in INR" v-model="price_inr" required />
			</div>
			<h6 class="mt-4 mb-4 text-lg font-semibold">Plan Features</h6>
			<ol class="grid grid-cols-1 gap-2 md:grid-cols-2">
				<li class="mt-1 flex" v-for="(feature, index) in features" :key="index">
					<div
						class="mx-2 flex w-7 items-center justify-center rounded-full bg-gray-200 text-sm text-gray-700"
					>
						{{ index + 1 }}
					</div>
					<Input type="text" v-model="feature.value" :key="feature" />
					<div
						class="mx-1 mt-1"
						v-on:click="
							() => {
								features.splice(index, 1);
							}
						"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="red"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
							class="feather feather-trash-2 mr-2 h-5 w-5"
						>
							<polyline points="3 6 5 6 21 6"></polyline>
							<path
								d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
							></path>
							<line x1="10" y1="11" x2="10" y2="17"></line>
							<line x1="14" y1="11" x2="14" y2="17"></line>
						</svg>
					</div>
				</li>
			</ol>
			<hr class="my-4" />
			<Input class="my-1" type="text" v-model="modelText" />
			<Button
				@click="
					() => {
						features.push({ idx: index + 1, value: modelText });
						modelText = '';
					}
				"
				type="secondary"
				>Add</Button
			>
		</Dialog>
	</div>
</template>
