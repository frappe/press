<template>
	<Dialog :options="{
		title: 'Normalized Slow Query',
		size: '2xl'
	}" v-model="show">
		<template #body-content>
			<div v-if="$site.doc?.version !== 'Version 14'"
				class="flex items-center space-x-2 p-3 bg-blue-100 rounded-lg border-blue-200 mb-5 text-sm text-gray-800 ">
				<i-lucide-info class="h-4 w-4" />
				<div>
					Upcoming Feature : Analyze Query coming soon on Version-15
				</div>
			</div>
			<pre class="rounded-lg border-2 border-gray-200 bg-gray-100 p-3 text-sm text-gray-700">
 {{ query }} </pre>
			<div class="flex p-2 text-sm">
				<span class="ml-auto pr-2">Duration: {{ duration.toFixed(2) }} seconds</span>
				<!-- <span class="pr-2">Rows Examined: {{ rows_examined}}</span>
				<span class="pr-2">Rows Sent: {{rows_sent}}</span>
				<span class="pr-2">Count: {{ count}}</span> -->
			</div>
		</template>
		<template v-if="$site.doc?.version === 'Version 14'" #actions>
			<Button class="w-full" :variant="'solid'" theme="gray" size="sm" label="Button"
				@click="$resources.analyzeQuery.submit()">
				Analyze Query
			</Button>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
export default {
	props: [
		'siteName',
		'query',
		'duration',
		'count',
		'rows_examined',
		'rows_sent',
		'example'
	],
	data() {
		return {
			show: true
		};
	},
	computed: {
		$site() {
			return getCachedDocumentResource("Site", this.siteName);
		}
	},
	resources: {
		analyzeQuery() {
			return {
				url: 'press.api.analytics.mariadb_analyze_query',
				makeParams() {
					return {
						rows: [
							{
								query: this.query,
								count: this.count,
								duration: this.duration,
								rows_examined: this.rows_examined,
								rows_sent: this.rows_sent,
								example: this.example
							}
						],
						name: this.siteName
					};
				},
				initialData: { data: [] }
			};
		}
	}
};
</script>
