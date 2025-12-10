<template>
	<ObjectList class="p-5" ref="objectList" :options="autoScaleRecords" />
</template>

<script>
import { h, defineAsyncComponent } from 'vue';
import { renderDialog } from '../../utils/components';
import { date } from '../../utils/format';
import { icon } from '../../utils/components';
import ObjectList from '../ObjectList.vue';

import Badge from '../global/Badge.vue';

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
					status: ['in', 'Scheduled'],
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
						type: 'Component',
						align: 'center',
						component: ({ row }) =>
							h(Badge, {
								label: row.action,
								theme: row.action === 'Scale Down' ? 'orange' : 'green',
							}),
					},
					{
						label: 'Scheduled Time',
						fieldname: 'scheduled_time',
						width: 1,
						format(row, value) {
							if (value.status !== 'Scheduled') {
								return '-';
							}
							return date(row, 'LLL');
						},
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

				primaryAction: () => ({
					label: 'Schedule Auto Scale',
					slots: { prefix: icon('clock') },
					onClick: () =>
						renderDialog(
							h(
								defineAsyncComponent(
									() => import('../server/AutoscaleScheduleDialog.vue'),
								),
								{
									server: this.name,
									reloadListView: this.$refs.objectList.reloadListView,
								},
							),
						),
				}),
			};
		},
	},
};
</script>
