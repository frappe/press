<template>
	<div class="flex h-60 flex-col items-center justify-center gap-1">
		<template v-if="isDedicatedServer">
			<p class="text-base text-ink-gray-7">
				Performance Schema is not enabled on database server
			</p>
			<p class="text-base text-ink-gray-7">
				Read the
				<a
					href="https://docs.frappe.io/cloud/performance-tuning"
					target="_blank"
					class="underline"
					>performance tuning guide</a
				>, or reach out to
				<a href="https://support.frappe.io/" target="_blank" class="underline"
					>support</a
				>
				to enable it
			</p>
		</template>
		<template v-else>
			<p class="text-base text-ink-gray-7">
				Performance Schema is disabled on shared hosting
			</p>
			<p class="text-base text-ink-gray-7">
				This feature is only available on a
				<a
					href="https://frappe.io/cloud/servers"
					target="_blank"
					class="underline"
					>dedicated server</a
				>
			</p>
		</template>
	</div>
</template>
<script>
export default {
	name: 'DatabasePerformanceSchemaDisabledNotice',
	props: {
		// support can only enable Performance Schema on a dedicated database
		// server, so a site on shared hosting must be told something different
		isDedicatedServer: {
			type: Boolean,
			default: false,
		},
	},
};
</script>
