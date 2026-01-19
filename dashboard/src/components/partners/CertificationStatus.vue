<template>
	<div>
		<Dialog
			:show="show"
			v-model="show"
			:options="{ title: 'Certification Request Status' }"
			size="xl"
		>
			<template #body-content>
				<ObjectList :options="requestList"></ObjectList>
			</template>
		</Dialog>
	</div>
</template>
<script setup>
import { ref, computed } from 'vue';
import { createResource } from 'frappe-ui';
import ObjectList from '../ObjectList.vue';

const show = ref(true);

const certRequestList = createResource({
	url: 'press.api.partner.get_certification_requests',
	auto: true,
	initialData: [],
	transform: (data) => {
		return (
			data?.map((row) => {
				return {
					member_name: row.name,
					certificate_type: row.course,
					status: row.status,
				};
			}) || []
		);
	},
});
const requestList = computed(() => {
	return {
		data: () => certRequestList.data,
		columns: [
			{
				label: 'Member Name',
				fieldname: 'member_name',
				width: 1,
			},
			{
				label: 'Certificate Type',
				fieldname: 'certificate_type',
				width: 1,
			},
			{
				label: 'Status',
				fieldname: 'status',
				width: 0.5,
				align: 'center',
				type: 'Badge',
			},
		],
		orderBy: 'creation desc',
	};
});
</script>
