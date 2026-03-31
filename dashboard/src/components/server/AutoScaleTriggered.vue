<template>
	<ObjectList class="p-5" :options="autoScaleRecords" />
</template>

<script>
import { h } from 'vue';
import { duration } from '../../utils/format';
import ObjectList from '../ObjectList.vue';
import Badge from '../global/Badge.vue';
import { renderDialog } from '../../utils/components';
import { defineAsyncComponent } from 'vue';

import { confirmDialog, icon } from '../../utils/components';
export default {
	name: 'AutoScale',
	props: {
		name: String,
	},

	components: { ObjectList, confirmDialog, icon },

	computed: {
		autoScaleRecords() {
			return {
				doctype: 'Auto Scale Record',
				filters: {
					primary_server: this.name,
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
				onRowClick: (row) => {
					this.$router.push({
						name: 'Auto Scale Steps',
						params: {
							id: row.name,
						},
					});
				},
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

				primaryAction: () => ({
					label: 'Configure Automated Scaling',
					slots: { prefix: icon('settings') },
					onClick: () => {
						renderDialog(
							h(
								defineAsyncComponent(
									() => import('../server/ConfigureAutomatedScaling.vue'),
								),
								{
									name: this.name,
								},
							),
						);
					},
				}),
			};
		},
	},
};
</script>
