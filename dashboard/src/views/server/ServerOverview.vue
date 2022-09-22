<script setup>
import { computed, ref } from 'vue';
import { utils } from '@/utils';
import useResource from '@/composables/resource';
import ServerOverviewInfo from './ServerOverviewInfo.vue';

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
			v-if="server && overview.data"
		>
			<ServerOverviewInfo :server="server" :info="overview.data.info" />
		</div>
	</div>
</template>
