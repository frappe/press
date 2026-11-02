<template>
	<div
		class="divide-y divide-outline-gray-2 [&>*:first-child]:pt-0 [&>*:last-child]:pb-0 [&>*]:py-8"
	>
		<ServerMalwareScan :server="id" />
		<ServerFirewall :id="id" />
	</div>
</template>

<script setup lang="ts">
import ServerFirewall from './ServerFirewall.vue'
import ServerMalwareScan from './ServerMalwareScan.vue'

defineProps<{
	id: string
}>()
</script>
