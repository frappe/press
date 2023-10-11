<template>
	<Card title="Uptime" :loading="loading">
		<div v-if="!data" class="flex h-full items-center justify-center">
			<div class="text-base text-gray-600">No data</div>
		</div>
		<div v-else class="mt-8" v-for="type in uptimeTypes" :key="type.key">
			<div class="flex h-8 justify-between">
				<div
					v-for="d in data"
					:key="d.date"
					style="width: 2.5px"
					:class="[
						d[type.key] === undefined
							? 'bg-white'
							: d[type.key] === 1
							? 'bg-green-500'
							: d[type.key] === 0
							? 'bg-red-500'
							: 'bg-yellow-500'
					]"
					:title="`${formatDate(d.date)} | Uptime: ${(d.value * 100).toFixed(
						2
					)}%`"
				></div>
			</div>
		</div>
	</Card>
</template>
<script>
import { DateTime } from 'luxon';
export default {
	name: 'SiteAnalyticsUptime',
	props: ['data', 'loading'],
	computed: {
		uptimeTypes() {
			return [{ key: 'value', label: 'Web' }];
		}
	},
	methods: {
		formatDate(date) {
			return DateTime.fromSQL(date).toLocaleString(DateTime.DATETIME_FULL);
		}
	}
};
</script>
