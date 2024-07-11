<template>
	<div class="space-y-4">
		<AlertBanner
			title="All metrics presented are from the last 24 hours."
			type="info"
		/>
		<div>
			<ObjectList :options="slowQueriesData" />
		</div>
	</div>
</template>

<script lang="jsx">
import { defineAsyncComponent, h } from 'vue';
import { ListView, FormControl, Dialog } from 'frappe-ui';
import ObjectList from '../../../src2/components/ObjectList.vue';
import AlertBanner from '../../../src2/components/AlertBanner.vue';
import { renderDialog } from '../../utils/components';

export default {
	name: 'SitePerformance',
	props: ['siteName'],
	components: {
		ListView,
		FormControl,
		Dialog,
		ObjectList,
		AlertBanner
	},
	data() {
		return {};
	},
	computed: {
		slowQueriesData() {
			return {
				data: () => this.$resources.slowQueries.data.data,
				onRowClick : (row)=> {
					const SlowQueryDialog = defineAsyncComponent(() =>
						import('./SiteMariaDBSlowQueryDialog.vue')
					);
					renderDialog(
						h(SlowQueryDialog, {

							siteName : this.siteName,
							query: row.query,
							duration: row.duration,
							count: row.count,
							rows_examined: row.rows_examined,
							rows_sent: row.rows_sent,
							example: row.example
						})
					);
				},
				columns: [
					{
						label: 'Query',
						fieldname: 'query',
						class: 'font-mono',
						width: '500px'
					},
					{
						label: 'Duration',
						fieldname: 'duration',
						class: 'text-gray-600',
						width: 0.5
					},
					{
						label: 'Rows Examined',
						fieldname: 'rows_examined',
						class: 'text-gray-600',
						width: 0.5
					},
					{
						label: 'Rows Sent',
						fieldname: 'rows_sent',
						class: 'text-gray-600',
						width: 0.5
					},
					{
						label: 'Count',
						fieldname: 'count',
						class: 'text-gray-600',
						width: 0.5
					}
				]
			};
		},
	},
	methods: {
		getDateTimeRange() {
			const now = new Date();
			const startDateTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
			const formatDateTime = date => {
				const year = date.getFullYear();
				const month = String(date.getMonth() + 1).padStart(2, '0');
				const day = String(date.getDate()).padStart(2, '0');
				const hours = String(date.getHours()).padStart(2, '0');
				const minutes = String(date.getMinutes()).padStart(2, '0');
				const seconds = String(date.getSeconds()).padStart(2, '0');
				return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
			};

			const endDateTime = formatDateTime(now);
			const startDateTimeFormatted = formatDateTime(startDateTime);

			return {
				startDateTime: startDateTimeFormatted,
				endDateTime: endDateTime
			};
		}
	},
	resources: {
		slowQueries() {
			const { startDateTime, endDateTime } = this.getDateTimeRange();
			return {
				url: 'press.api.analytics.mariadb_slow_queries',
				params: {
					name: this.siteName,
					start_datetime: startDateTime,
					stop_datetime: endDateTime,
					max_lines: 10,
					search_pattern: '.*',
					normalize_queries: true,
					analyze: false
				},
				auto: true,
				initialData: { columns: [], data: [] }
			};
		}
	}
};
</script>
