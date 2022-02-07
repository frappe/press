<template>
	<Card title="Uptime">
		<div class="mt-8" v-for="type in uptimeTypes" :key="type.key">
			<div class="flex h-8 justify-between">
				<div
					v-for="d in data"
					:key="d.timestamp"
					style="width: 2px"
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
		</div>
	</Card>
</template>
<script>
export default {
	name: 'SiteAnalyticsUptime',
	props: ['data'],
	computed: {
		uptimeTypes() {
			return [{ key: 'value', label: 'Web' }];
		}
	}
};
</script>
