<template>
	<div class="p-5">
		<div class="flex items-center space-x-2">
			<Button
				:route="{
					name:
						object.doctype === 'Site'
							? 'Site Logs'
							: `${object.doctype} Detail Logs`,
				}"
			>
				<template #icon>
					<lucide-arrow-left class="inline-block h-4 w-4" />
				</template>
			</Button>
			<h2 class="text-lg font-medium text-gray-900">{{ logName }}</h2>
			<div class="!ml-auto flex gap-2">
				<Button
					:route="{
						name: 'Log Browser',
						params: {
							mode: object.doctype === 'Site' ? 'site' : 'bench',
							docName: name,
							logId: logName,
						},
					}"
				>
					<template #prefix>
						<lucide-sparkle class="h-4 w-4" />
					</template>
					View in Log Browser
				</Button>
				<Button
					@click="$resources.log.reload()"
					:loading="$resources.log.loading"
				>
					<template #icon>
						<lucide-refresh-ccw class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>

		<div class="mt-3">
			<div class="mt-8 space-y-4">
				<div
					class="overflow-auto relative rounded border border-gray-100 bg-surface-gray-7 p-5 px-5.5 text-sm text-gray-200"
				>
					<CopyBtn :text="log" class="absolute right-3 top-3" />

					<span v-if="$resources.log.loading" class="flex items-center gap-2">
						<Spinner /> Loading...</span
					>
					<pre v-else>{{ log || 'No output' }}</pre>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { FeatherIcon, Spinner } from 'frappe-ui';
import { getObject } from '../objects';
import { unreachable } from '../objects/common';
import CopyBtn from '@/components/utils/CopyBtn.vue';

export default {
	name: 'LogPage',
	props: ['name', 'logName', 'objectType'],
	components: { FeatherIcon },
	resources: {
		log() {
			const url = this.forSite ? 'press.api.site.log' : 'press.api.bench.log';
			const params = { log: this.logName, name: this.name };
			if (!this.forSite) {
				params.name = `bench-${this.name?.split('-')[1]}`;
				params.bench = this.name;
			}

			return {
				url,
				params,
				auto: true,
				transform(log) {
					return log[this.logName];
				},
				onSuccess() {
					this.lastLoaded = Date.now();
				},
			};
		},
	},
	computed: {
		forSite() {
			if (this.objectType === 'Site') return true;
			if (this.objectType === 'Bench') return false;
			throw unreachable;
		},
		object() {
			return getObject(this.objectType);
		},
		log() {
			return this.$resources.log.data;
		},
	},
};
</script>
