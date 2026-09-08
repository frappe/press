<template>
	<div class="flex h-60 flex-col items-center justify-center gap-1">
		<template v-if="isDedicatedServer">
			<p class="text-base text-ink-gray-7">
				Please refer to the
				<a
					href="https://docs.frappe.io/cloud/performance-tuning"
					target="_blank"
					class="underline"
					>performance tuning documentation</a
				>
			</p>
			<p class="text-base text-ink-gray-7">
				For any other concern, raise a support ticket on
				<a href="https://support.frappe.io/" target="_blank" class="underline"
					>support.frappe.io</a
				>
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
