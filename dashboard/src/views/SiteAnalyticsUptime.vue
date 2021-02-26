<template>
	<Card title="Uptime">
		<div class="mt-8" v-for="type in uptimeTypes" :key="type.key">
			<div class="flex justify-between h-4">
				<div
					v-for="d in data"
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
	</Card>
</template>
<script>
export default {
	name: 'SiteAnalyticsUptime',
	props: ['data'],
	computed: {
		uptimeTypes() {
			return [
				{ key: 'web', label: 'Web' },
				{ key: 'scheduler', label: 'Scheduler' }
				// { key: 'socketio', label: 'SocketIO' }
			];
		}
	}
};
</script>
