<template>
	<div v-if="$site.doc.current_plan.monitor_access" class="m-5">
		<!-- <Report
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
			v-if="$resources.binaryLogs.loading"
		>
			<LoadingText />
		</div>
		<div
			class="py-2 text-base text-gray-600"
			v-else-if="$resources.binaryLogs.data.length == 0"
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
		</Button> -->
		<ObjectList :options="binaryLogsOptions" />
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 text-base text-gray-700">
			Your plan doesn't support this feature. Please upgrade your plan.
		</span>
	</div>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import Report from '@/components/Report.vue';
import ObjectList from '../../ObjectList.vue';
import dayjs from '../../../utils/dayjs';

export default {
	name: 'SiteBinaryLogs',
	props: ['name'],
	components: { Report, ObjectList },
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
			today: dayjs().format('YYYY-MM-DD HH:mm:ss'),
			yesterday: dayjs().subtract(1, 'day').format('YYYY-MM-DD HH:mm:ss'),
			max_lines: 4000
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
	methods: {
		reset() {
			this.$resources.binaryLogs.reset();
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
						params: {
							name: this.name,
							start_time: this.startTime || this.yesterday,
							end_time: this.endTime || this.today,
							pattern: this.patternFilter,
							max_lines: this.max_lines
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
				filterControls() {
					return [
						{
							type: 'datetime',
							label: 'Version',
							fieldname: 'version',
							options: {
								doctype: 'Frappe Version'
							}
						}
					];
				}
			};
		},
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
