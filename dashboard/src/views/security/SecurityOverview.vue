<script setup>
import { createResource } from 'frappe-ui';
import SecurityUpdatesOverview from './SecurityUpdatesOverview.vue';
import FirewallOverview from './FirewallOverview.vue';

const props = defineProps({ server: Object });
</script>

<template>
	<div class="space-y-5" v-if="server">
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="server">
			<SecurityUpdatesOverview :server="server" />
			<FirewallOverview :server="server" />
		</div>
	</div>
</template>
