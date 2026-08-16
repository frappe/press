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
			<h2 class="text-lg font-medium text-ink-gray-9">{{ logName }}</h2>
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

		<div
			class="mt-5 flex rounded bg-surface-gray-7 dark:bg-surface-gray-1 p-4 text-sm text-ink-gray-2 dark:text-ink-gray-8"
		>
			<span v-if="$resources.log.loading" class="flex items-center gap-2">
				<Spinner />
				Loading...
			</span>

			<pre ref="logBody" v-else class="flex-1 min-w-0 overflow-auto">{{
				log || 'No output'
			}}</pre>

			<CopyBtn :text="log" class="pl-1 ml-auto mb-auto shrink-0 -mr-1 -mt-1" />
		</div>
	</div>
</template>

<script>
import { FeatherIcon, Spinner } from 'frappe-ui'
import CopyBtn from '@/components/utils/CopyBtn.vue'
import { getObject } from '../objects'
import { unreachable } from '../objects/common'

export default {
	name: 'LogPage',
	props: ['name', 'logName', 'objectType'],
	components: { FeatherIcon },
	resources: {
		log() {
			const url = this.forSite ? 'press.api.site.log' : 'press.api.bench.log'
			const params = { log: this.logName, name: this.name }
			if (!this.forSite) {
				params.name = `bench-${this.name?.split('-')[1]}`
				params.bench = this.name
			}

			return {
				url,
				params,
				auto: true,
				transform(log) {
					return log[this.logName]
				},
				onSuccess() {
					this.lastLoaded = Date.now()
					// the newest entries are at the end, and these files run to megabytes.
					// scrollIntoView walks up to whichever ancestor actually scrolls.
					this.$nextTick(() =>
						this.$refs.logBody?.scrollIntoView({ block: 'end' }),
					)
				},
			}
		},
	},
	computed: {
		forSite() {
			if (this.objectType === 'Site') return true
			if (this.objectType === 'Bench') return false
			throw unreachable
		},
		object() {
			return getObject(this.objectType)
		},
		log() {
			return this.$resources.log.data
		},
	},
}
</script>
