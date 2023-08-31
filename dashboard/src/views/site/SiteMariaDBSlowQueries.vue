<template>
	<div v-if="$resources.getPlan.data.monitor_access">
		<Card>
			<Report
				:filters="filters"
				:columns="[
					{ label: 'Timestamp', name: 'timestamp', class: 'w-2/12' },
					{ label: 'Query', name: 'query', class: 'w-7/12' },
					{ label: 'Duration', name: 'duration', class: 'w-1/12' },
					{ label: 'Rows Examined', name: 'examined', class: 'w-1/12' },
					{ label: 'Rows Sent', name: 'sent', class: 'w-1/12' }
				]"
				:data="formatSlowQueries"
				title="MariaDB Slow Queries Report"
			/>
			<div
				class="px-2 py-2 text-base text-gray-600"
				v-if="
					$resources.slowQueries.loading &&
					$resources.slowQueries.data.length == 0
				"
			>
				<LoadingText />
			</div>
			<div
				class="py-2 text-base text-gray-600"
				v-if="
					!$resources.slowQueries.loading &&
					$resources.slowQueries.data.length == 0
				"
			>
				No data
			</div>
			<Button
				v-if="$resources.slowQueries.data && $resources.slowQueries.data.length"
				:loading="$resources.slowQueries.loading"
				loadingText="Loading..."
				@click="max_lines += 20"
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
	name: 'SiteMariaDBSlowQueries',
	props: ['site'],
	components: {
		Report
	},
	data() {
		return {
			filters: [
				{
					name: 'pattern',
					label: 'Search:',
					type: 'text',
					value: this.pattern
				},
				{ name: 'start', label: 'From:', type: 'datetime-local', value: '' },
				{ name: 'end', label: 'To:', type: 'datetime-local', value: '' }
			],
			max_lines: 20
		};
	},
	watch: {
		pattern() {
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
		slowQueries() {
			return {
				url: 'press.api.analytics.mariadb_slow_queries',
				params: {
					site: this.site?.name,
					start: this.startTime || this.today,
					end: this.endTime || this.today,
					pattern: this.pattern,
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
			this.$resources.slowQueries.reset();
		}
	},
	computed: {
		startTime() {
			return this.filters[1].value;
		},
		endTime() {
			return this.filters[2].value;
		},
		pattern() {
			return this.filters[0].value;
		},
		formatSlowQueries() {
			let data = [];
			this.$resources.slowQueries.data.forEach(row => {
				let time = this.formatDate(row.timestamp, 'TIME_24_WITH_SHORT_OFFSET');
				let out = [
					{ name: 'Timestamp', value: time, class: 'w-2/12' },
					{ name: 'Query', value: row.query, class: 'w-7/12' },
					{ name: 'Duration', value: row.duration, class: 'w-1/12' },
					{ name: 'Examined', value: row.rows_examined, class: 'w-1/12' },
					{ name: 'Sent', value: row.sent, class: 'w-1/12' }
				];
				data.push(out);
			});
			return data;
		}
	}
};
</script>
