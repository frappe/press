<template>
	<div v-if="$site.doc?.current_plan?.monitor_access" class="m-5">
		<ObjectList :options="requestLogsOptions" />
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 p-2 text-base text-gray-800">
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
	name: 'SiteRequestLogs',
	props: ['name'],
	components: {
		ObjectList
	},
	data() {
		return {
			date: null,
			start: 0
		};
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.name);
		},
		requestLogsOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.request_logs',
						makeParams: params => {
							// for filterControls to work
							if (params) return params;

							return {
								name: this.name,
								timezone: dayjs.tz.guess(),
								sort: 'CPU Time (Descending)',
								date: this.today,
								start: this.start
							};
						},
						auto: true,
						initialData: [],
						transform: data => {
							return data.map(log => {
								log.time = dayjs(log.timestamp).format('HH:mm:ss z');
								log.method = log.request.method;
								log.path = log.request.path;
								log.status = log.request.status_code;
								log.cpu_time = log.duration / 1000000;
								return log;
							});
						}
					};
				},
				columns: [
					{ label: 'Time', fieldname: 'time', width: 1 },
					{ label: 'Method', fieldname: 'method', width: 0.5 },
					{ label: 'Path', fieldname: 'path', width: 2, class: 'font-mono' },
					{ label: 'Status Code', fieldname: 'status', width: 0.5 },
					{
						label: 'CPU Time (seconds)',
						fieldname: 'cpu_time',
						width: 1,
						class: 'text-gray-600'
					}
				],
				filterControls: () => [
					{
						type: 'select',
						label: 'Sort',
						fieldname: 'sort',
						class: !this.$isMobile ? 'w-48' : '',
						options: [
							'Time (Ascending)',
							'Time (Descending)',
							'CPU Time (Descending)'
						],
						default: 'CPU Time (Descending)'
					},
					{
						type: 'date',
						label: 'Date',
						fieldname: 'date',
						class: !this.$isMobile ? 'w-48' : '',
						default: this.today
					}
				],
				actions: () => [
					{
						label: 'Back',
						icon: 'arrow-left',
						onClick: () => {
							this.$router.push({ name: 'Site Detail Performance' });
						}
					}
				]
			};
		},
		today() {
			return dayjs().format('YYYY-MM-DD');
		}
	},
	methods: {
		showPlanChangeDialog() {
			const SitePlansDialog = defineAsyncComponent(() =>
				import('../../ManageSitePlansDialog.vue')
			);
			renderDialog(h(SitePlansDialog, { site: this.name }));
		}
	}
};
</script>
