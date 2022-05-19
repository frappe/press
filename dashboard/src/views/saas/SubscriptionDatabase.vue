<script setup>
import { computed } from 'vue';
import SiteDatabaseBackups from '../SiteDatabaseBackups.vue';
import SiteDatabaseRestore from '../SiteDatabaseRestore.vue';
import useResource from '@/composables/resource.js';

const props = defineProps({ subData: Object });
</script>

<template>
	<div class="grid grid-cols-1 gap-5 sm:grid-cols-2" v-if="subData">
		<SiteDatabaseBackups :site="subData.site" />
		<div><SiteDatabaseRestore :site="subData.site" /></div>
	</div>
</template>
