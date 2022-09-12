<script setup>
import { computed, ref } from 'vue';
import { utils } from '@/utils';
import useResource from '@/composables/resource';

const props = defineProps({ server: Object });

const overview = useResource({
	method: 'press.api.server.overview',
	params: { name: props.server?.name },
	keepData: true,
	auto: true
});
</script>

<template>
	<div class="space-y-5" v-if="server">
		<div
			class="grid grid-cols-1 gap-5 sm:grid-cols-2"
			v-if="site && overview.data"
		></div>
	</div>
</template>
