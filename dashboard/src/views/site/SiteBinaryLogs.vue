<template>
	<div v-if="$resources.getPlan.data.monitor_access">
		<Card>
			<Report
				:filters="filters"
				:columns="[
					{ label: 'Timestamp', name: 'timestamp', class: 'w-3/12' },
					{ label: 'Query', name: 'query', class: 'w-9/12' }
				]"
				:data="formatData"
				title="MariaDB Binary Log Report"
			/>
			<div
				class="px-2 py-2 text-base text-gray-600"
				v-if="
					$resources.binaryLogs.loading &&
					$resources.binaryLogs.data.length == 0
				"
			>
				<LoadingText />
			</div>
			<div
				class="py-2 text-base text-gray-600"
				v-if="
					!$resources.binaryLogs.loading &&
					$resources.binaryLogs.data.length == 0
				"
			>
				No data
			</div>
			<Button
				v-if="$resources.binaryLogs.data && $resources.binaryLogs.data.length"
				:loading="$resources.binaryLogs.loading"
				loadingText="Loading..."
				@click="max_lines += 10"
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
import Report from '@/components/Report.vue';

export default {
	name: 'SiteBinaryLogs',
	props: ['site'],
	components: { Report },
	data() {
		return {
			filters: [
				{
					name: 'pattern',
					label: 'Search:',
					type: 'text',
					value: this.pattern
				},
				{
					name: 'start_datetime',
					label: 'From:',
					type: 'datetime-local',
					value: ''
				},
				{
					name: 'end_datetime',
					label: 'To:',
					type: 'datetime-local',
					value: ''
				}
			],
			max_lines: 100
		};
	},
	watch: {
		patternFilter() {
			this.reset();
		},
		startTime() {
			this.reset();
		},
		endTime() {
			this.reset();
		}
	},
	resources: {
		binaryLogs() {
			return {
				method: 'press.api.analytics.binary_logs',
				params: {
					name: this.site?.name,
					start_time: this.startTime || this.today,
					end_time: this.endTime || this.today,
					pattern: this.patternFilter,
					max_lines: this.max_lines
				},
				auto: true,
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
			this.$resources.binaryLogs.reset();
		}
	},
	computed: {
		startTime() {
			return this.filters[1].value;
		},
		endTime() {
			return this.filters[2].value;
		},
		patternFilter() {
			return this.filters[0].value;
		},
		formatData() {
			let binaryData = this.$resources.binaryLogs.data;
			let data = [];
			binaryData.forEach(row => {
				let timestamp = this.formatDate(
					row.timestamp,
					'TIME_24_WITH_SHORT_OFFSET'
				);
				let out = [
					{ name: 'Timestamp', value: timestamp, class: 'w-3/12' },
					{ name: 'Query', value: row.query, class: 'w-9/12' }
				];
				data.push(out);
			});
			return data;
		}
	}
};
</script>
