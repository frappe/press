<template>
	<div v-if="$resources.getPlan.data.monitor_access">
		<Card>
			<Report
				title="Request Logs"
				:columns="[
					{ label: 'Time', name: 'time', class: 'w-2/12' },
					{ label: 'Method', name: 'method', class: 'w-1/12' },
					{ label: 'Path', name: 'path', class: 'w-5/12' },
					{ label: 'Status Code', name: 'status', class: 'w-2/12' },
					{ label: 'CPU Time (seconds)', name: 'cpu_time', class: 'w-2/12' }
				]"
				:data="formatData"
				:filters="[sortFilter, dateFilter]"
			/>

			<div
				class="px-2 py-2 text-base text-gray-600"
				v-if="
					$resources.requestLogs.loading &&
					$resources.requestLogs.data.length == 0
				"
			>
				<LoadingText />
			</div>
			<div
				class="py-2 text-base text-gray-600"
				v-if="
					!$resources.requestLogs.loading &&
					$resources.requestLogs.data.length == 0
				"
			>
				No data
			</div>
			<Button
				v-if="$resources.requestLogs.data && $resources.requestLogs.data.length"
				:loading="$resources.requestLogs.loading"
				loadingText="Loading..."
				@click="start += 10"
			>
				Load more
			</Button>
		</Card>
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 text-base text-gray-700">
			Your plan doesn't support this feature. Please upgrade your plan.
		</span>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import Report from '@/components/Report.vue';

export default {
	name: 'SiteRequestLogs',
	props: ['site'],
	components: {
		Report
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
	resources: {
		requestLogs() {
			return {
				method: 'press.api.analytics.request_logs',
				params: {
					name: this.site?.name,
					timezone: DateTime.local().zoneName,
					sort: this.sortFilter.value,
					date: this.dateFilter.value || this.today,
					start: this.start
				},
				auto: Boolean(this.today),
				pageLength: 10,
				keepData: true,
				default: []
			};
		},
		getPlan() {
			return {
				method: 'press.api.site.current_plan',
				params: {
					name: this.site?.name
				},
				auto: true
			};
		}
	},
	methods: {
		reset() {
			this.$resources.requestLogs.reset();
			this.start = 0;
		}
	},
	computed: {
		today() {
			return DateTime.local().toISODate();
		},
		formatData() {
			let requestData = this.$resources.requestLogs.data;
			let data = [];
			requestData.forEach(log => {
				log.time = this.formatDate(log.timestamp, 'TIME_24_WITH_SHORT_OFFSET');
				log.method = log.request.method;
				log.path = log.request.path;
				log.status = log.request.status_code;
				log.cpu_time = this.$formatCPUTime(log.duration);

				let row = [
					{ name: 'Time', value: log.time, class: 'w-2/12' },
					{ name: 'Method', value: log.method, class: 'w-1/12' },
					{ name: 'Path', value: log.path, class: 'w-5/12 break-all pr-2' },
					{ name: 'Status', value: log.status, class: 'w-2/12' },
					{ name: 'CPU Time', value: log.cpu_time, class: 'w-2/12' }
				];
				data.push(row);
			});
			return data;
		}
	}
};
</script>
