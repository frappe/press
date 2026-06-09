<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Dialog, TextInput, Button, Checkbox, createResource } from 'frappe-ui'

interface Props {
	bench: any
}

const show = ref(true)
const props = defineProps<Props>()
const searchQuery = ref('')
const subdomain = ref('')
const addedApps = reactive<any[]>([])
const siteOptions = ref<any>({})

const emit = defineEmits<{ siteCreated: [] }>()

const handleAppSelection = (cond: boolean, app: any) => {
	if (cond) addedApps.push(app)
	else addedApps.splice(addedApps.indexOf(app), 1)
}

const installableApps = createResource({
	url: 'press.api.site.options_for_new',
	auto: true,
	makeParams() {
		return { for_bench: props.bench.name }
	},
	transform(data: any) {
		const version = data.versions?.[0]
		siteOptions.value = {
			domain: data.domain,
			group: version?.group?.name,
			cluster: version?.group?.clusters?.[0]?.name,
		}
		const sources = version?.group?.bench_app_sources || []
		return sources
			.map((sourceName: string) => {
				const src = data.app_source_details?.[sourceName] || {}
				const mp = data.marketplace_details?.[src.app] || {}
				return {
					app: src.app,
					source: sourceName,
					title: mp.title || src.app_title,
					image: mp.image,
					description: mp.description,
				}
			})
			.filter((a: any) => a.app && a.app !== 'frappe')
	},
})

const newSite = createResource({
	url: 'press.api.client.insert',
	onSuccess() {
		emit('siteCreated')
		show.value = false
	},
})

const submitForm = () => {
	newSite.submit({
		doc: {
			doctype: 'Site',
			subdomain: subdomain.value,
			apps: [{ app: 'frappe' }, ...addedApps.map((x: any) => ({ app: x.app }))],
			cluster: siteOptions.value.cluster,
			group: siteOptions.value.group,
			domain: siteOptions.value.domain,
		},
	})
}
</script>

<template>
	<Dialog v-model="show" :options="{ title: 'Add Site', size: '2xl' }">
		<template #body-content>
			<div class="flex flex-col gap-5">
				<div class="flex items-center gap-0">
					<TextInput
						placeholder="mysite"
						v-model="subdomain"
						class="rounded-r-none"
					/>
					<div
						class="flex items-center rounded-r border border-l-0 bg-surface-gray-2 px-3 h-7 text-sm text-ink-gray-6"
					>
						.{{ siteOptions.domain }}
					</div>
				</div>

				<TextInput
					placeholder="Search for any Frappe app"
					v-model="searchQuery"
					:debounce="500"
				>
					<template #prefix>
						<lucide-search class="size-4 text-ink-gray-5" />
					</template>
				</TextInput>
				<div class="grid grid-cols-2 gap-4">
					<label
						class="p-3 text-sm transition-colors duration-300 border rounded flex gap-2 has-[:checked]:border-outline-gray-5 hover:border-outline-gray-3"
						v-for="app in installableApps.data"
						:key="app.app"
					>
						<div class="p-2 rounded bg-surface-gray-2 row-span-full h-fit">
							<img v-if="app.image" :src="app.image" class="size-4 rounded" />
							<LucideBox v-else class="size-4" />
						</div>
						<div class="flex flex-col leading-relaxed overflow-hidden">
							<span class="font-medium">{{ app.title }}</span>
							<span class="text-ink-gray-5 truncate"
								>{{ app?.description }}</span
							>
						</div>
						<Checkbox @update:modelValue="(x) => handleAppSelection(x, app)" />
					</label>
				</div>
				<div class="flex">
					<Button
						variant="solid"
						class="ml-auto"
						@click="submitForm"
						:loading="newSite.loading"
					>
						Create Site
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
