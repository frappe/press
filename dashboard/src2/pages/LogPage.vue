<template>
	<div class="p-5">
		<div class="flex items-center space-x-2">
			<Button
				:route="{
					name:
						object.doctype === 'Site'
							? 'Site Logs'
							: `${object.doctype} Detail Logs`
				}"
			>
				<template #icon>
					<i-lucide-arrow-left class="inline-block h-4 w-4" />
				</template>
			</Button>
			<h2 class="text-lg font-medium text-gray-900">{{ logName }}</h2>
			<Button
				class="!ml-auto"
				@click="$resources.log.reload()"
				:loading="$resources.log.loading"
			>
				<template #icon>
					<i-lucide-refresh-ccw class="h-4 w-4" />
				</template>
			</Button>
		</div>

		<div class="mt-3">
			<div class="mt-8 space-y-4">
				<div
					class="overflow-auto rounded border border-gray-100 bg-gray-900 px-2.5 py-2 text-sm text-gray-200"
				>
					<pre>{{
						$resources.log.loading ? 'Loading...' : log || 'No output'
					}}</pre>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import { FeatherIcon } from 'frappe-ui';
import { getObject } from '../objects';
import { unreachable } from '../objects/common';

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
				}
			};
		}
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
		}
	}
};
</script>
