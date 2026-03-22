<template>
	<div class="flex divide-x p-5">
		<div class="w-1/3">
			<template v-for="tab in tabs">
				<router-link
					:to="{ name: tab.value, params: { nc: tab.name } }"
					class="flex my-4 mr-4 justify-between gap-6 border rounded cursor-pointer text-base text-gray-600 hover:bg-gray-100"
					:class="{
						' bg-gray-50 text-gray-800': isActiveTab(tab),
						'text-gray-600': !isActiveTab(tab),
					}"
				>
					<div class="p-4">
						<div>{{ tab.label }}</div>
						<Badge :theme="theme_map[tab.status]" :label="tab.status" />
					</div>
				</router-link>
			</template>
		</div>
		<div class="w-2/3 overflow-auto">
			<router-view />
		</div>
	</div>
</template>
<script setup>
import { onMounted, defineProps, ref } from 'vue';
import router from '../../router';
import { createListResource } from 'frappe-ui';

const props = defineProps({
	partner_audit: {
		type: String,
		required: true,
	},
});

const tabs = ref([]);

const theme_map = {
	Open: 'blue',
	Closed: 'green',
	WIP: 'orange',
};

const ncList = createListResource({
	doctype: 'Partner Non Conformance',
	filters: {
		partner_audit: props.partner_audit,
	},
	auto: true,
	fields: [
		'name',
		'department',
		'nc_description',
		'nc_statement',
		'auditor',
		'raised_on',
		'status',
	],
	onSuccess() {
		tabs.value = ncList.data.map((nc) => ({
			label: nc.name,
			value: 'PartnerNCSummary',
			name: nc.name,
			status: nc.status,
		}));
	},
});

const isActiveTab = (tab) => {
	return [tab.value, ...(tab.children || [])].find(
		(child) => child === router.currentRoute.value.name,
	);
};

onMounted(() => {
	if (router.currentRoute.value.name === 'PartnerNCList') {
		router.replace({ name: 'PartnerNCSummary' });
	}
});
</script>
