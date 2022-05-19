<script setup>
import useResource from '@/composables/resource.js';
import { computed } from 'vue';
import AppCard from './AppCard.vue';

const saasApps = useResource({
	method: 'press.api.saas.get_saas_apps',
	auto: true
});

const apps = computed(() => {
	console.log(saasApps.data);
	return saasApps.data;
});
</script>
<template>
	<div class="mt-8 flex-1">
		<Alert class="mb-4" title="Subscription" type="warning">
			Signup with one of the apps below and get a 14 days free trial.
		</Alert>
		<div class="grid grid-cols-1 gap-1 md:grid-cols-3" v-if="apps">
			<AppCard v-for="app in apps" :key="app.title" :app="app" />
		</div>
	</div>
</template>
