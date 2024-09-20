<template>
	<div v-if="$site.doc.current_plan.monitor_access" class="m-5">
		<ObjectList :options="binaryLogsOptions" />
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 text-base text-gray-700">
			Your plan doesn't support this feature. Please
			<span class="cursor-pointer underline" @click="showPlanChangeDialog"
				>upgrade your plan</span
			>
			.
		</span>
	</div>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { defineAsyncComponent, h } from 'vue';
import { renderDialog } from '../../../utils/components';
import ObjectList from '../../ObjectList.vue';
import dayjs from '../../../utils/dayjs';

export default {
	name: 'SiteBinaryLogs',
	props: ['name'],
	components: { ObjectList },
	data() {
		return {
			today: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			yesterday: dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
			max_lines: 4000
		};
	},
	methods: {
		showPlanChangeDialog() {
			const SitePlansDialog = defineAsyncComponent(() =>
				import('../../ManageSitePlansDialog.vue')
			);
			renderDialog(h(SitePlansDialog, { site: this.name }));
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.name);
		},
		binaryLogsOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.binary_logs',
						makeParams: params => {
							if (params) return params;

							return {
								name: this.name,
								start_time: this.yesterday,
								end_time: this.today,
								pattern: '.*',
								max_lines: this.max_lines
							};
						},
						auto: true,
						pageLength: 10,
						keepData: true,
						initialData: []
					};
				},
				columns: [
					{
						label: 'Timestamp',
						fieldname: 'timestamp',
						width: '12rem',
						format: value => {
							return this.$format.date(value, 'YYYY-MM-DD HH:mm:ss');
						}
					},
					{ label: 'Query', fieldname: 'query', class: 'font-mono' }
				],
				actions: () => [
					{
						label: 'Back',
						icon: 'arrow-left',
						onClick: () => {
							this.$router.push({
								name: 'Site Detail Performance'
							});
						}
					}
				],
				filterControls: () => {
					return [
						{
							type: 'datetime',
							label: 'Start Time',
							fieldname: 'start_time',
							default: this.yesterday
						},
						{
							type: 'datetime',
							label: 'End Time',
							fieldname: 'end_time',
							default: this.today
						},
						{
							label: 'Pattern',
							fieldname: 'pattern',
							default: '.*'
						},
						{
							label: 'Max Lines',
							fieldname: 'max_lines',
							default: 4000
						}
					];
				}
			};
		}
	}
};
</script>
