<template></template>
<script>
import ObjectList from '../components/ObjectList.vue';
export default {
	name: 'BillingSubscriptions',
	props: ['tab'],
	components: {
		ObjectList,
	},
	computed: {
		options() {
			return {
				doctype: 'Subscription',
				fields: [],
				filterControls: () => {
					return [];
				},
				columns: [
					{
						label: 'Name',
						fieldname: 'name',
					},
					{
						label: 'Resource',
						fieldname: 'document_type',
					},
					{
						label: 'Resource Name',
						fieldname: 'document_name',
					},
					{
						label: 'Plan',
						fieldname: 'plan',
					},
				],
				orderBy: 'creation desc',
			};
		},
	},
};
</script>
