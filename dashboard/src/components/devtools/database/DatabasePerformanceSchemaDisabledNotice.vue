<template>
	<div class="flex h-60 flex-col items-center justify-center gap-1">
		<p class="text-base text-gray-700">
			Performance Schema is not enabled on database server
		</p>
		<p class="text-base text-gray-700">
			Please reach out to
			<a href="https://support.frappe.io/" target="_blank" class="underline"
				>support</a
			>
			to enable it
		</p>
	</div>
</template>
<script>
export default {
	name: 'DatabasePerformanceSchemaDisabledNotice',
};
</script>
