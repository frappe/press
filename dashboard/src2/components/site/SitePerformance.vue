<template>
	<div class="space-y-4">
		<FormControl
			class="w-32"
			label="Duration"
			type="select"
			:options="durationOptions"
			v-model="duration"
		/>
		<div>
			<ObjectList :options="slowQueriesData" />
		</div>
	</div>
</template>

<script>
import { ListView, FormControl, Dialog } from 'frappe-ui';
import ObjectList from '../../../src2/components/ObjectList.vue';

export default {
	name: 'SitePerformance',
	props: ['siteName'],
	components: {
		ListView,
		FormControl,
		Dialog,
		ObjectList
	},
	data() {
		return {
			duration: '24h',
			durationOptions: [
				{ label: '1 hour', value: '1h' },
				{ label: '6 hours', value: '6h' },
				{ label: '24 hours', value: '24h' },
				{ label: '7 days', value: '7d' },
				{ label: '15 days', value: '15d' }
			]
		};
	},
	computed: {
		slowQueriesData() {
			return {
				data: () => this.$resources.slowQueries.data.data,
				columns: [
					{
						label: 'Query',
						fieldname: 'query',
						width : "500px"
					},
					{
						label: 'Duration',
						fieldname: 'duration',
						class: 'text-gray-600',
						width : 0.5
					},
					{
						label: 'Rows Examined',
						fieldname: 'rows_examined',
						class: 'text-gray-600',
						width : 0.5

					},
					{
						label: 'Rows Sent',
						fieldname: 'rows_sent',
						class: 'text-gray-600',
						width : 0.5

					},
					{
						label: 'Count',
						fieldname: 'count',
						class: 'text-gray-600',
						width : 0.5

					}
				]
			};
		}
	},
	resources: {
		slowQueries() {
			return {
				url: 'press.api.analytics.mariadb_slow_queries',
				params: {
					name: this.siteName,
					start_datetime: '2024-07-01 10:09:51',
					stop_datetime: '2024-07-09 10:09:51',
					max_lines: 10,
					search_pattern: '.*',
					normalize_queries: true,
					analyze: false
				},
				auto: true,
				initialData :{columns: [],data:[]},
			};
		}
	}
};
</script>
