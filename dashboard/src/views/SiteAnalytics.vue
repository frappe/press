<template>
	<div>
		<section>
			<div class="flex justify-between">
				<div>
					<h2 class="font-medium text-lg">Analytics</h2>
					<p class="text-gray-600">Realtime usage analytics of your site</p>
				</div>
				<div>
					<select class="form-select">
						<option
							v-for="o in periodOptions"
							:value="o"
							:selected="period === o"
						>
							{{ o }}
						</option>
					</select>
				</div>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-4" v-if="analytics">
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>Requests per minute</div>
					<div ref="requests-per-minute"></div>
				</div>
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>CPU usage per minute</div>
					<div ref="requests-cpu-usage"></div>
				</div>
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>Background Jobs per minute</div>
					<div ref="jobs-per-minute"></div>
				</div>
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>Background Jobs CPU usage per minute</div>
					<div ref="jobs-cpu-usage"></div>
				</div>
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>Uptime</div>
					<div>
						<div class="mt-8" v-for="type in uptimeTypes">
							<div class="flex justify-between h-4">
								<div
									v-for="d in analytics.uptime"
									style="width: 2px;"
									:class="[d[type.key] ? 'bg-green-500' : 'bg-red-500']"
								></div>
							</div>
							<div class="mt-2 text-sm flex justify-between">
								<span>
									{{ type.label }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import { DateTime } from 'luxon';
import { Chart } from 'frappe-charts/dist/frappe-charts.esm.js';

export default {
	name: 'SiteAnalytics',
	props: ['site'],
	data() {
		return {
			analytics: null,
			period: '6 hours',
			periodOptions: ['6 hours', '24 hours', '7 days', '30 days'],
			uptimeTypes: [
				{ key: 'web', label: 'Web' },
				{ key: 'scheduler', label: 'Scheduler' },
				{ key: 'socketio', label: 'SocketIO' }
			]
		};
	},
	async mounted() {
		await this.fetchAnalytics();
		this.makeRequestsPerSecondChart();
		this.makeJobsPerSecondChart();
		this.makeCPUUsageChart();
		this.makeJobCPUUsageChart();
	},
	methods: {
		async fetchAnalytics() {
			this.analytics = await this.$call('press.api.site.analytics', {
				name: this.site.name,
				period: this.period
			});
		},
		makeRequestsPerSecondChart() {
			new Chart(this.$refs['requests-per-minute'], {
				data: {
					labels: this.analytics.requests_per_minute.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{ values: this.analytics.requests_per_minute.map(d => d.value) }
					]
				},
				type: 'line',
				colors: ['red'],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-mm-yyyy hh:mm a');
					},
					formatTooltipY: d => d + ' requests'
				}
			});
		},
		makeJobsPerSecondChart() {
			new Chart(this.$refs['jobs-per-minute'], {
				data: {
					labels: this.analytics.jobs_per_minute.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{ values: this.analytics.jobs_per_minute.map(d => d.value) }
					]
				},
				type: 'line',
				colors: ['red'],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-mm-yyyy hh:mm a');
					},
					formatTooltipY: d => d + ' jobs'
				}
			});
		},
		makeCPUUsageChart() {
			new Chart(this.$refs['requests-cpu-usage'], {
				data: {
					labels: this.analytics.request_cpu_time_per_minute.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{
							values: this.analytics.request_cpu_time_per_minute.map(
								d => d.value / 1000
							)
						}
					]
				},
				type: 'line',
				colors: ['blue'],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-mm-yyyy hh:mm a');
					},
					formatTooltipY: d => {
						return d + 's';
					}
				}
			});
		},
		makeJobCPUUsageChart() {
			new Chart(this.$refs['jobs-cpu-usage'], {
				data: {
					labels: this.analytics.job_cpu_time_per_minute.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{
							values: this.analytics.job_cpu_time_per_minute.map(
								d => d.value / 1000
							)
						}
					]
				},
				type: 'line',
				colors: ['blue'],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-mm-yyyy hh:mm a');
					},
					formatTooltipY: d => {
						return d + 's';
					}
				}
			});
		}
	}
};
</script>

<style>
.frappe-chart .line-vertical {
	display: none;
}
</style>
