<template>
	<ObjectList class="p-5" :options="autoScaleRecords" />
</template>

<script>
import { duration } from '../../utils/format';
import ObjectList from '../ObjectList.vue';

export default {
	name: 'AutoScale',
	props: {
		name: String,
	},

	components: { ObjectList },

	computed: {
		autoScaleRecords() {
			return {
				doctype: 'Auto Scale Record',
				filters: {
					primary_server: this.name,
					secondary_server: this.$route.query.secondaryServer,
					status: ['not in', 'Scheduled'],
				},
				filterControls: () => [
					{
						type: 'select',
						label: 'Action',
						fieldname: 'action',
						options: ['', 'Scale Down', 'Scale Up'],
					},
					{
						type: 'text',
						label: 'Triggered By',
						fieldname: 'owner',
					},
				],

				orderBy: 'creation desc',

				fields: ['owner'],

				columns: [
					{ label: 'Secondary Server', fieldname: 'secondary_server' },

					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge',
						align: 'center',
					},
					{
						label: 'Action',
						fieldname: 'action',
						type: 'Badge',
						align: 'center',
					},
					{
						label: 'Duration',
						fieldname: 'duration',
						width: 1,
						format: (row) => (row ? duration(row) : '-'),
					},
					{
						label: 'Created By',
						fieldname: 'owner',
						align: 'center',
					},
					{
						label: 'Created At',
						fieldname: 'creation',
						type: 'Timestamp',
						align: 'right',
					},
				],
			};
		},
	},
};
</script>
