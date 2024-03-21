<template>
	<Dialog
		:options="{
			title: `Bench Logs - ${bench}`,
			size: '6xl'
		}"
		v-model="show"
	>
		<template #body-content>
			<ObjectList v-if="!showLog" :options="listOptions" />
			<div v-else class="p-5">
				<div class="flex items-center">
					<Button @click="showLog = false">
						<template #icon>
							<i-lucide-arrow-left class="inline-block h-4 w-4" />
						</template>
					</Button>
					<h2 class="ml-4 text-lg font-medium text-gray-900">{{ logName }}</h2>
					<Button class="!ml-auto" @click="log.reload()" :loading="log.loading">
						<template #icon>
							<i-lucide-refresh-ccw class="h-4 w-4" />
						</template>
					</Button>
				</div>
				<div class="mt-3">
					<div>
						<div class="flex items-center space-x-2"></div>
					</div>
					<div class="mt-8 space-y-4">
						<div
							class="overflow-auto rounded border border-gray-100 bg-gray-900 px-2.5 py-2 text-sm text-gray-200"
						>
							<pre>{{
								log.loading ? 'Loading...' : log?.data[logName] || 'No output'
							}}</pre>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { createResource } from 'frappe-ui';
import { defineProps, ref } from 'vue';
import ObjectList from '../ObjectList.vue';
import { date } from '../../utils/format';

const props = defineProps({
	bench: String
});

const show = ref(true);
const logName = ref('');
const showLog = ref(false);

const log = createResource({
	url: 'press.api.bench.log',
	makeParams() {
		return {
			name: `bench-${props.bench?.split('-')[1]}`,
			bench: props.bench,
			log: logName.value
		};
	}
});

const listOptions = ref({
	resource() {
		return {
			url: 'press.api.bench.logs',
			makeParams() {
				return {
					name: `bench-${props.bench?.split('-')[1]}`,
					bench: props.bench
				};
			},
			auto: true
		};
	},
	onRowClick(row) {
		logName.value = row.name;
		showLog.value = true;
		log.fetch();
	},
	columns: [
		{
			label: 'Name',
			fieldname: 'name'
		},
		{
			label: 'Size',
			fieldname: 'size',
			class: 'text-gray-600',
			format(value) {
				return `${value} kB`;
			}
		},
		{
			label: 'Created On',
			fieldname: 'created',
			format(value) {
				return value ? date(value, 'lll') : '';
			}
		}
	]
});
</script>
