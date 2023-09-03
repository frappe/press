<template>
	<div
		class="flex items-center justify-center"
		v-if="$resources.getPlan?.loading"
	>
		<LoadingText />
	</div>
	<div v-else-if="$resources.getPlan?.data?.monitor_access">
		<Card>
			<Report
				:filters="filters"
				:columns="[
					{ label: 'Timestamp', name: 'timestamp', class: 'w-2/12' },
					{ label: 'Query', name: 'query', class: 'w-10/12' }
				]"
				:data="formatDeadlockData"
				title="MariaDB Deadlock Report"
			/>
			<div
				class="px-2 py-2 text-base text-gray-600"
				v-if="
					$resources.deadlockReport.loading &&
					$resources.deadlockReport.data.length == 0
				"
			>
				<LoadingText />
			</div>
			<div
				class="content-center py-2 text-base"
				v-if="
					!$resources.deadlockReport.loading &&
					$resources.deadlockReport.data.length == 0
				"
			>
				No data
			</div>
			<Button
				v-if="
					$resources.deadlockReport.data &&
					$resources.deadlockReport.data.length
				"
				:loading="$resources.deadlockReport.loading"
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
import { DateTime } from 'luxon';

export default {
	name: 'SiteDeadlockReport',
	props: ['site'],
	components: {
		Report
	},
	data() {
		return {
			filters: [
				{
					name: 'start_datetime',
					label: 'From:',
					type: 'date',
					value: this.today
				},
				{ name: 'end_datetime', label: 'To:', type: 'date', value: this.today }
			],
			max_lines: 20
		};
	},
	watch: {
		startTime() {
			this.reset();
		},
		endTime() {
			this.reset();
		}
	},
	resources: {
		deadlockReport() {
			return {
				url: 'press.api.analytics.deadlock_report',
				params: {
					site: this.site?.name,
					start: this.startTime || this.today,
					end: this.endTime || this.today,
					max_lines: this.max_lines
				},
				auto: true,
				pageLength: 10,
				keepData: true,
				initialData: []
			};
		},
		getPlan() {
			return {
				url: 'press.api.site.current_plan',
				params: {
					name: this.site?.name
				},
				auto: true
			};
		}
	},
	methods: {
		reset() {
			this.$resources.deadlockReport.reset();
		}
	},
	computed: {
		today() {
			return DateTime.local().toISODate();
		},
		startTime() {
			return this.filters[0].value;
		},
		endTime() {
			return this.filters[1].value;
		},
		formatDeadlockData() {
			let data = [];
			this.$resources.deadlockReport.data.forEach(row => {
				let timestamp = this.formatDate(
					row.timestamp,
					'TIME_24_WITH_SHORT_OFFSET'
				);
				let out = [
					{ name: 'Timestamp', value: timestamp, class: 'w-2/12' },
					{ name: 'Query', value: row.query, class: 'w-10/12' }
				];
				data.push(out);
			});

			return data;
		}
	}
};
</script>
