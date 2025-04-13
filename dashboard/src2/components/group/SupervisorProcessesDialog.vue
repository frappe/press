<template>
	<Dialog
		:options="{
			title: `Processes - ${bench}`,
			size: '4xl'
		}"
		v-model="show"
	>
		<template #body-content>
			<ObjectList :options="listOptions" />
		</template>
	</Dialog>
</template>

<script lang="ts" setup>
import { defineProps, ref } from 'vue';
import { getProcessesColumns } from '../../objects/bench';
import ObjectList from '../ObjectList.vue';

const props = defineProps({
	bench: String
});
const show = ref(true);

const listOptions = ref({
	resource() {
		return {
			url: 'press.api.bench.get_processes',
			params: { name: props.bench },
			auto: true
		};
	},
	emptyStateMessage: 'No processes found.',
	columns: getProcessesColumns(),
	selectable: false
});
</script>
