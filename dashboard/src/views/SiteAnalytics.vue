<template>
	<div>
		<section>
			<div class="flex justify-between">
				<div>
					<h2 class="text-lg font-medium">Analytics</h2>
					<p class="text-base text-gray-600">
						Realtime usage analytics of your site
					</p>
				</div>
				<div>
					<select class="form-select" v-model="period">
						<option
							v-for="o in periodOptions"
							:value="o"
							:selected="period === o"
							:key="o"
						>
							{{ o }}
						</option>
					</select>
				</div>
			</div>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2" v-if="analytics">
				<div class="px-6 py-4 mt-6 border rounded shadow">
					<div>Requests per minute</div>
					<div ref="requests-per-minute"></div>
				</div>
				<div class="px-6 py-4 mt-6 border rounded shadow">
					<div>CPU usage per minute</div>
					<div ref="requests-cpu-usage"></div>
				</div>
				<div class="px-6 py-4 mt-6 border rounded shadow">
					<div>Background Jobs per minute</div>
					<div ref="jobs-per-minute"></div>
				</div>
				<div class="px-6 py-4 mt-6 border rounded shadow">
					<div>Background Jobs CPU usage per minute</div>
					<div ref="jobs-cpu-usage"></div>
				</div>
				<div class="px-6 py-4 mt-6 border rounded shadow">
					<div>Uptime</div>
					<div>
						<div class="mt-8" v-for="type in uptimeTypes" :key="type.key">
							<div class="flex justify-between h-4">
								<div
									v-for="d in analytics.uptime"
									:key="d.timestamp"
									style="width: 2px;"
									:class="[
										d[type.key] === 1
											? 'bg-green-500'
											: d[type.key] === 0
											? 'bg-red-500'
											: 'bg-orange-500'
									]"
								></div>
							</div>
							<div class="flex justify-between mt-2 text-sm">
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
			period: '1 hour',
			periodOptions: ['1 hour', '6 hours', '24 hours', '7 days', '30 days'],
			uptimeTypes: [
				{ key: 'web', label: 'Web' },
				{ key: 'scheduler', label: 'Scheduler' }
				// { key: 'socketio', label: 'SocketIO' }
			]
		};
	},
	watch: {
		period() {
			this.refreshCharts();
		}
	},
	mounted() {
		this.refreshCharts();
	},
	methods: {
		async fetchAnalytics() {
			this.analytics = await this.$call('press.api.site.analytics', {
				name: this.site.name,
				period: this.period
			});
		},
		async refreshCharts() {
			await this.fetchAnalytics();
			this.makeRequestsPerSecondChart();
			this.makeJobsPerSecondChart();
			this.makeCPUUsageChart();
			this.makeJobCPUUsageChart();
		},
		makeRequestsPerSecondChart() {
			new Chart(this.$refs['requests-per-minute'], {
				data: {
					labels: this.analytics.request_count.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [{ values: this.analytics.request_count.map(d => d.value) }]
				},
				type: 'line',
				colors: ['red'],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true,
					spline: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-MM-yyyy hh:mm a');
					},
					formatTooltipY: d => d + ' requests'
				}
			});
		},
		makeJobsPerSecondChart() {
			new Chart(this.$refs['jobs-per-minute'], {
				data: {
					labels: this.analytics.job_count.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [{ values: this.analytics.job_count.map(d => d.value) }]
				},
				type: 'line',
				colors: ['red'],
				axisOptions: {
					xIsSeries: true,
					shortenYAxisNumbers: 1
				},
				lineOptions: {
					hideDots: true,
					spline: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-MM-yyyy hh:mm a');
					},
					formatTooltipY: d => d + ' jobs'
				}
			});
		},
		makeCPUUsageChart() {
			new Chart(this.$refs['requests-cpu-usage'], {
				data: {
					labels: this.analytics.request_cpu_time.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{
							values: this.analytics.request_cpu_time.map(d => d.value / 1000)
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
					hideDots: true,
					spline: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-MM-yyyy hh:mm a');
					},
					formatTooltipY: d => {
						return d + ' ms';
					}
				}
			});
		},
		makeJobCPUUsageChart() {
			new Chart(this.$refs['jobs-cpu-usage'], {
				data: {
					labels: this.analytics.job_cpu_time.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{
							values: this.analytics.job_cpu_time.map(d => d.value / 1000)
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
					hideDots: true,
					spline: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-MM-yyyy hh:mm a');
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
