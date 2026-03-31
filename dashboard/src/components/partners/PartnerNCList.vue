<template>
	<div class="flex divide-x p-5">
		<div class="w-1/5">
			<div class="text-lg text-gray-600 flex">Non Conformance List</div>
			<template v-for="tab in tabs">
				<router-link
					:to="{ name: tab.value, params: { nc: tab.name } }"
					class="flex p-4 my-4 mr-4 justify-between border gap-6 rounded cursor-pointer text-base text-gray-600 hover:bg-gray-100"
					:class="{
						'text-gray-800 bg-gray-50': isActiveTab(tab),
						'text-gray-400': !isActiveTab(tab),
					}"
				>
					<div>{{ tab.label }}</div>
					<Badge :theme="theme_map[tab.status]" :label="tab.status" />
				</router-link>
			</template>
		</div>
		<div class="w-3/5 overflow-auto">
			<router-view />
		</div>
	</div>
</template>
<script setup>
import { onMounted, defineProps, ref } from 'vue';
import router from '../../router';
import { createListResource } from 'frappe-ui';
import { useRoute } from 'vue-router';

const route = useRoute();

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
			label: nc.nc_statement,
			value: 'PartnerNCSummary',
			name: nc.name,
			status: nc.status,
		}));
	},
	orderBy: 'modified desc',
});

const isActiveTab = (tab) => {
	return [tab.name].find((child) => child === route.params.nc);
};

onMounted(() => {
	if (route.name === 'PartnerNCList') {
		router.replace({ name: 'PartnerNCSummary' });
	}
});
</script>
