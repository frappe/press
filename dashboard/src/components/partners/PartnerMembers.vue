<template>
	<div class="px-2">
		<GenericList :options="partnerMembersList" />
	</div>
</template>
<script setup>
import { computed } from 'vue';
import GenericList from '../GenericList.vue';
import { createResource } from 'frappe-ui';

const props = defineProps({
	partnerName: String,
});

const partnerMembers = createResource({
	url: 'press.api.partner.get_partner_members',
	cache: 'partnerMembers',
	auto: true,
	params: {
		partner: props.partnerName,
	},
	transform(data) {
		data = data.map((d) => {
			return {
				full_name: d.member_name,
				email: d.member_email,
				course:
					d.course == 'frappe-developer-certification'
						? 'Framework'
						: 'ERPNext',
				version: d.version,
			};
		});
		return data;
	},
});

const partnerMembersList = computed(() => {
	return {
		data: partnerMembers.data || [],
		selectable: false,
		columns: [
			{
				label: 'Name',
				fieldname: 'full_name',
			},
			{
				label: 'Email',
				fieldname: 'email',
			},
			{
				label: 'Course',
				fieldname: 'course',
				width: 0.6,
			},
			{
				label: 'Version',
				fieldname: 'version',
				width: 0.5,
				align: 'center',
			},
		],
	};
});
</script>
