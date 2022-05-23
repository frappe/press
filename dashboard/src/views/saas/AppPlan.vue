<script setup>
import FeatureList from '@/components/FeatureList.vue';
import { computed, ref } from 'vue';
import useResource from '@/composables/resource';
import call from '../../controllers/call';

const props = defineProps({ app: Object });
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
		name: props.app.name
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
		name: props.app.name
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
	<Card
		title="Manage Plans"
		:subtitle="`Add, remove or edit plans for ${app.title} App.`"
	>
		<template #actions>
			<Button icon-left="plus" @click="showCreateDialog = true"
				>Add Plan</Button
			>
		</template>
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
						class="mx-2 text-gray-700 rounded-full bg-gray-200 flex items-center justify-center text-sm w-7"
					>
						{{ index + 1 }}
					</div>
					<Input type="text" v-model="feature.value" :key="feature" />
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
						class="mx-2 text-gray-700 rounded-full bg-gray-200 flex items-center justify-center text-sm w-7"
					>
						{{ index + 1 }}
					</div>
					<Input type="text" v-model="feature.value" :key="feature" />
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
	</Card>
</template>
