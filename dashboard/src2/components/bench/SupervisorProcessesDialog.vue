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
import ObjectList from '../ObjectList.vue';
import { h } from 'vue';
import { Tooltip } from 'frappe-ui';
import { icon } from '../../utils/components';
import { ref, defineProps } from 'vue';

interface Process {
	program: string;
	name: string;
	status: string;
	uptime?: number;
	uptime_string?: string;
	message?: string;
	group?: string;
	pid?: number;
}

const props = defineProps({
	bench: String
});
const show = ref(true);

const BADGE_COLORS = {
	Starting: 'blue',
	Backoff: 'yellow',
	Running: 'green',
	Stopping: 'yellow',
	Stopped: 'gray',
	Exited: 'gray',
	Unknown: 'gray',
	Fatal: 'red'
};

const listOptions = ref({
	resource() {
		return {
			url: 'press.api.bench.get_processes',
			params: { name: props.bench },
			auto: true
		};
	},
	emptyStateMessage: 'No processes found.',
	columns: [
		{
			label: 'Name',
			width: 2,
			fieldname: 'name'
		},
		{
			label: 'Group',
			width: 1.5,
			fieldname: 'group',
			format: v => v ?? ''
		},
		{
			label: 'Status',
			type: 'Badge',
			width: 0.7,
			fieldname: 'status',
			theme: (value: string) => BADGE_COLORS[value] ?? 'gray',
			suffix({ message }: Process) {
				if (!message) {
					return;
				}

				return h(
					Tooltip,
					{
						text: message,
						placement: 'top'
					},
					() => h(icon('alert-circle', 'w-3 h-3'))
				);
			}
		},
		{
			label: 'Uptime',
			fieldname: 'uptime_string'
		}
	],
	selectable: false
});
</script>
