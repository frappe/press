<template>
	<div>
		<PerformanceReport
			title="Slow Queries"
			:site="name"
			:reportOptions="slowQueriesOptions"
		/>
		<SiteSlowQueryDialog
			v-if="show"
			v-model="show"
			:query="selectedQuery"
			:duration="selectedQueryDuration"
		/>
	</div>
</template>

<script>
import AlertBanner from '../../AlertBanner.vue';
import PerformanceReport from './PerformanceReport.vue';
import SiteSlowQueryDialog from './SiteSlowQueryDialog.vue';

export default {
	props: ['name', 'siteVersion'],
	components: {
		PerformanceReport,
		AlertBanner,
		SiteSlowQueryDialog,
	},
	data() {
		return {
			show: false,
			selectedQuery: '',
			selectedQueryDuration: 0,
		};
	},
	computed: {
		slowQueriesOptions() {
			return {
				experimental: true,
				documentation: 'https://docs.frappe.io/cloud/performance-tuning',
				data: () => this.$resources.slowQueries.data.data,
				onRowClick: (row) => {
					this.selectedQuery = row.query;
					this.selectedQueryDuration = row.duration;
					this.show = true;
				},
				emptyStateMessage: 'No slow queries found',
				columns: [
					{
						label: 'Query',
						fieldname: 'query',
						class: 'font-mono',
						width: '600px',
					},
					{
						label: 'Duration',
						fieldname: 'duration',
						class: 'text-gray-600',
						width: 0.3,
						align: 'right',
						format: (value) => value.toFixed(2),
					},
					{
						label: 'Rows Examined',
						fieldname: 'rows_examined',
						class: 'text-gray-600',
						align: 'right',
						width: 0.3,
					},
					{
						label: 'Rows Sent',
						fieldname: 'rows_sent',
						class: 'text-gray-600',
						align: 'right',
						width: 0.3,
					},
					{
						label: 'Count',
						fieldname: 'count',
						class: 'text-gray-600',
						align: 'right',
						width: 0.3,
					},
				],
				actions: () => [
					{
						label: 'Refresh',
						icon: 'refresh-ccw',
						loading: this.$resources.slowQueries.loading,
						onClick: () => this.$resources.slowQueries.reload(),
					},
				],
			};
		},
	},
	methods: {
		getDateTimeRange() {
			const formatDateTime = (date) => {
				return this.$dayjs(date).format('YYYY-MM-DD HH:mm:ss');
			};

			const now = new Date();
			const startDateTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
			const endDateTime = formatDateTime(now);
			const startDateTimeFormatted = formatDateTime(startDateTime);

			return {
				startDateTime: startDateTimeFormatted,
				endDateTime: endDateTime,
			};
		},
	},
	resources: {
		slowQueries() {
			const { startDateTime, endDateTime } = this.getDateTimeRange();
			return {
				url: 'press.api.analytics.mariadb_slow_queries',
				params: {
					name: this.name,
					start_datetime: startDateTime,
					stop_datetime: endDateTime,
					max_lines: 10,
					search_pattern: '.*',
					normalize_queries: true,
					analyze: false,
				},
				auto: true,
				initialData: { columns: [], data: [] },
			};
		},
	},
};
</script>
