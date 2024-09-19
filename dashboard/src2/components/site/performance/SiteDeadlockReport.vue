<template>
	<div v-if="$site.doc?.current_plan?.monitor_access" class="m-5">
		<!-- <Card>
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
		</Card> -->
		<ObjectList :options="deadlockReportOptions" />
	</div>
	<div class="flex justify-center" v-else>
		<span class="mt-16 text-base text-gray-700">
			Your plan doesn't support this feature. Please upgrade your plan.
		</span>
	</div>
</template>
<script>
import Report from '@/components/Report.vue';
import { getCachedDocumentResource } from 'frappe-ui';
import { DateTime } from 'luxon';
import ObjectList from '../../ObjectList.vue';

export default {
	name: 'SiteDeadlockReport',
	props: ['name'],
	components: {
		Report,
		ObjectList
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
					site: this.name,
					start: this.startTime || this.today,
					end: this.endTime || this.today
				},
				auto: true,
				initialData: []
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
		$site() {
			return getCachedDocumentResource('Site', this.name);
		},
		deadlockReportOptions() {
			return {
				resource: () => {
					return {
						url: 'press.api.analytics.deadlock_report',
						params: {
							site: this.name,
							start: this.startTime || this.today,
							end: this.endTime || this.today
						},
						auto: true,
						initialData: []
					};
				},
				columns: [
					{ label: 'Timestamp', fieldname: 'timestamp' },
					{ label: 'Query', fieldname: 'query' }
				],
				actions: () => {
					return [
						{
							label: 'Back',
							icon: 'arrow-left',
							onClick: () => {
								this.$router.push({ name: 'Site Detail Performance' });
							}
						}
					];
				}
			};
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
