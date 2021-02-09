<template>
	<div class="space-y-4">
		<div>
			<label class="flex items-baseline space-x-2" for="">
				<div class="text-base font-medium">Showing analytics of last</div>
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
			</label>
		</div>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="analytics">
			<Card title="Usage Counter">
				<div ref="usage-counter"></div>
			</Card>

			<Card title="Uptime">
				<div>
					<div class="mt-8" v-for="type in uptimeTypes" :key="type.key">
						<div class="flex justify-between h-4">
							<div
								v-for="d in analytics.uptime"
								:key="d.timestamp"
								style="width: 2px;"
								:class="[
									d[type.key] === undefined
										? 'bg-white'
										: d[type.key] === 1
										? 'bg-green-500'
										: d[type.key] === 0
										? 'bg-red-500'
										: 'bg-yellow-500'
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
			</Card>

			<Card title="Requests">
				<div ref="requests-per-minute"></div>
			</Card>

			<Card title="CPU Usage">
				<div ref="requests-cpu-usage"></div>
			</Card>
			<Card title="Background Jobs">
				<div ref="jobs-per-minute"></div>
			</Card>
			<Card title="Background Jobs CPU Usage">
				<div ref="jobs-cpu-usage"></div>
			</Card>
		</div>
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
			periodOptions: ['1 hour', '6 hours', '24 hours', '7 days'],
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
			this.analytics = await this.$call('press.api.analytics.get', {
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
			this.makeUsageCounterChart();
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
							values: this.analytics.request_cpu_time.map(
								d => d.value / 1000000
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
					hideDots: true,
					spline: true
				},
				tooltipOptions: {
					formatTooltipX: d => {
						return DateTime.fromSQL(d.timestamp).toFormat('dd-MM-yyyy hh:mm a');
					},
					formatTooltipY: d => {
						return d + ' s';
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
							values: this.analytics.job_cpu_time.map(d => d.value / 1000000)
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
		},
		makeUsageCounterChart() {
			new Chart(this.$refs['usage-counter'], {
				data: {
					labels: this.analytics.usage_counter.map(d => {
						return {
							timestamp: d.timestamp,
							toString() {
								return DateTime.fromSQL(d.timestamp).toFormat('hh:mm a');
							}
						};
					}),
					datasets: [
						{
							values: this.analytics.usage_counter.map(d => d.value / 1000000)
						}
					],
					yMarkers: [
						{ label: 'Daily CPU Time Limit', value: this.analytics.plan_limit }
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
						return d + ' s';
					}
				}
			});
		}
	}
};
</script>
