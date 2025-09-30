<template>
	<Dialog
		:options="{
			title: `Bench Logs - ${bench}`,
			size: '6xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<ObjectList v-if="!showLog" :options="listOptions" />
			<div v-else>
				<div class="flex items-center">
					<Button @click="showLog = false">
						<template #icon>
							<lucide-arrow-left class="inline-block h-4 w-4" />
						</template>
					</Button>
					<h2 class="ml-4 text-lg font-medium text-gray-900">{{ logName }}</h2>
					<div class="!ml-auto flex gap-2">
						<Button @click="log.reload()" :loading="log.loading">
							<template #icon>
								<lucide-refresh-ccw class="h-4 w-4" />
							</template>
						</Button>
						<Button @click="navigateToLogBrowser">
							<template #prefix>
								<lucide-sparkle class="h-4 w-4" />
							</template>
							View in Log Browser
						</Button>
					</div>
				</div>
				<div class="mt-4">
					<div
						class="h-[34rem] overflow-scroll rounded border border-gray-100 bg-gray-900 px-2.5 py-2 text-sm text-gray-200"
					>
						<pre>{{
							log.loading ? 'Loading...' : log?.data[logName] || 'No output'
						}}</pre>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { createResource } from 'frappe-ui';
import { defineProps, h, ref } from 'vue';
import LucideSparkleIcon from '~icons/lucide/sparkle';
import ObjectList from '../ObjectList.vue';
import { date } from '../../utils/format';
import router from '../../router';

const props = defineProps({
	bench: String,
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
			log: logName.value,
		};
	},
});

const navigateToLogBrowser = () => {
	show.value = false;
	router.push({
		name: 'Log Browser',
		params: {
			mode: 'bench',
			docName: props.bench,
			logId: logName.value,
		},
	});
};

const listOptions = ref({
	resource() {
		return {
			url: 'press.api.bench.logs',
			makeParams() {
				return {
					name: `bench-${props.bench?.split('-')[1]}`,
					bench: props.bench,
				};
			},
			cache: ['BenchLogs', props.bench],
			auto: true,
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
			fieldname: 'name',
		},
		{
			label: 'Size',
			fieldname: 'size',
			class: 'text-gray-600',
			format(value) {
				return `${value} kB`;
			},
		},
		{
			label: 'Created On',
			fieldname: 'created',
			format(value) {
				return value ? date(value, 'lll') : '';
			},
		},
	],
	actions: () => [
		{
			slots: {
				prefix: () => h(LucideSparkleIcon),
			},
			label: 'View in Log Browser',
			onClick: () => {
				show.value = false;
				router.push({
					name: 'Log Browser',
					params: { mode: 'bench', docName: props.bench },
				});
			},
		},
	],
});
</script>
