<template>
	<div v-if="$site.doc?.current_plan?.monitor_access" class="m-5">
		<ObjectList :options="requestLogsOptions" />
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 text-base text-gray-700">
			Your plan doesn't support this feature. Please upgrade your plan.
		</span>
	</div>
</template>

<script>
import dayjs from '../../../utils/dayjs';
import Report from '@/components/Report.vue';
import { getCachedDocumentResource } from 'frappe-ui';
import ObjectList from '../../ObjectList.vue';

export default {
	name: 'SiteRequestLogs',
	props: ['name'],
	components: {
		Report,
		ObjectList
	},
	data() {
		return {
			date: null,
			sort: 'CPU Time (Descending)',
			start: 0,
			sortFilter: {
				name: 'sort',
				options: [
					'Time (Ascending)',
					'Time (Descending)',
					'CPU Time (Descending)'
				],
				type: 'select',
				value: 'CPU Time (Descending)'
			},
			dateFilter: {
				name: 'date',
				type: 'date',
				value: null
			}
		};
	},
	watch: {
		sort(value) {
			this.reset();
		}
	},
	methods: {
		reset() {
			this.$resources.requestLogs.reset();
			this.start = 0;
		}
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.name);
		},
		requestLogsOptions() {
			return {
				resource: l => {
					console.log(l.filters);
					return {
						url: 'press.api.analytics.request_logs',
						makeParams: () => {
							return {
								name: this.name,
								timezone: dayjs.tz.guess(),
								sort: this.sortFilter.value,
								date: this.dateFilter.value || this.today,
								start: this.start
							};
						},
						// auto: Boolean(this.today),
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
			return dayjs().toISOString();
		}
	}
};
</script>
