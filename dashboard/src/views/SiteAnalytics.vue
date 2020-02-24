<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Analytics</h2>
			<p class="text-gray-600">Realtime usage analytics of your site</p>
			<div class="grid grid-cols-2 gap-4">
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>Requests per second</div>
					<div ref="req-per-second"></div>
				</div>
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>Uptime</div>
					<div>
						<div class="mt-8" v-for="d in uptime">
							<div class="flex justify-between h-4">
								<div
									v-for="tick in d.ticks"
									style="width: 2px;"
									:class="[tick ? 'bg-green-500' : 'bg-red-500']"
								></div>
							</div>
							<div class="mt-2 text-sm flex justify-between">
								<span>
									{{ d.name }}
								</span>
								<span class="text-gray-600">90 days</span>
							</div>
						</div>
					</div>
				</div>
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>Scheduler Health</div>
					<div ref="scheduler-health"></div>
				</div>
				<div class="mt-6 shadow rounded border border-gray-100 px-6 py-4">
					<div>CPU usage per minute</div>
					<div ref="cpu-usage"></div>
				</div>
			</div>
		</section>
	</div>
</template>

<script>
import { Chart } from 'frappe-charts/dist/frappe-charts.esm.js';

export default {
	name: 'SiteAnalytics',
	props: ['site'],
	data() {
		return {
			uptime: [
				{
					name: 'Web Requests',
					ticks: Array.from(new Array(90)).map(d => {
						return Math.random() < 0.8;
					})
				},
				{
					name: 'Scheduler',
					ticks: Array.from(new Array(90)).map(d => {
						return Math.random() < 0.8;
					})
				},
				{
					name: 'Socket.io',
					ticks: Array.from(new Array(90)).map(d => {
						return Math.random() < 0.8;
					})
				}
			]
		};
	},
	mounted() {
		this.makeRequestsPerSecondChart();
		this.makeSchedulerHealthChart();
		this.makeCPUUsageChart();
	},
	methods: {
		makeRequestsPerSecondChart() {
			new Chart(this.$refs['req-per-second'], {
				data: {
					labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
					datasets: [{ values: [18, 40, 30, 35, 8, 52, 17, -4] }]
				},
				type: 'line',
				colors: ['red']
			});
		},
		makeCPUUsageChart() {
			new Chart(this.$refs['cpu-usage'], {
				data: {
					labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
					datasets: [{ values: [340, 140, 230, 135, 118, 152, 417, 70] }]
				},
				type: 'line',
				colors: ['blue']
			});
		},
		makeSchedulerHealthChart() {
			new Chart(this.$refs['scheduler-health'], {
				data: {
					labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
					datasets: [
						{ name: 'Worker 1', values: [18, 40, 30, 35, 8, 52, 17, -4] },
						{ name: 'Worker 2', values: [20, 30, 15, 40, 16, 3, 24, 27] },
						{ name: 'Worker 3', values: [29, 12, 30, 24, 45, 32, 20, 28] }
					]
				},
				type: 'line',
				colors: ['red']
			});
		}
	}
};
</script>
