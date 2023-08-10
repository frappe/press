<template>
	<div class="space-y-5" v-if="server">
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="server">
			<SecurityUpdatesOverview :server="server" />
			<FirewallOverview :server="server" />
		</div>
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="server">
			<SSHOverview :server="server" />
		</div>
	</div>
</template>

<script setup>
import SecurityUpdatesOverview from './SecurityUpdatesOverview.vue';
import FirewallOverview from './FirewallOverview.vue';
import SSHOverview from './SSHOverview.vue';

const props = defineProps({ server: Object });
</script>
