<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
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
const formType = ref('addApps')

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

const filteredApps = computed(() => {
	const apps = installableApps.data ?? []
	const query = searchQuery.value.trim().toLowerCase()
	if (!query) return apps

	return apps.filter(
		(app: any) =>
			app.title?.toLowerCase().includes(query) ||
			app.description?.toLowerCase().includes(query) ||
			app.app?.toLowerCase().includes(query),
	)
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
			<template v-if="formType == 'addApps'">
				<div class="flex items-center gap-x-2 mb-5 flex-wrap leading-relaxed">
					<span class="font-medium">Add apps from your bench</span>
					<LucideBoxes class="size-3.5" />
					{{ bench.title }}

					<span class="bg-surface-gray-4 size-1.5 rounded-full mx-1" />
					<LucidePackage class="size-3.5" />
					{{ bench.version }}

					<p class="text-ink-gray-5">
						Only apps installed on the site's bench are available for
						installation.
					</p>
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
						v-for="app in filteredApps"
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
			</template>

			<template v-else>
				<label> Name your new site </label>
				<TextInput
					placeholder="Enter site name"
					v-model="subdomain"
					variant="outline"
					class="mt-3"
				>
					<template #suffix>
						<div
							class="flex items-center border-x rounded-r -mr-[7px]  bg-surface-gray-2 px-2 h-6.5 text-sm text-ink-gray-6"
						>
							.{{ siteOptions.domain }}
						</div>
					</template>
				</TextInput>

				<div class="leading-relaxed mt-5">
					<span class="font-medium"
						>Product warranty enabled for this site
					</span>

					<p class="text-ink-gray-5">
						Support covers only issues of Frappe apps and not functional
						queries. You can raise a support ticket for Frappe Cloud issues
						anytime.
					</p>
				</div>
			</template>

			<div class="flex gap-2 mt-5">
				<a
					class="flex items-center gap-2 text-ink-gray-5"
					href="https://docs.frappe.io/cloud/installing-an-app#sites-on-private-bench-groups"
					v-if="formType == 'addApps'"
				>
					<LucideInfo class="size-4" />
					Looking for Marketplace Apps?
				</a>

				<Button v-else variant="ghost" @click="formType = 'addApps'">
					<template #prefix>
						<LucideChevronLeft class="size-4" />
					</template>
					Back
				</Button>

				<Button class="ml-auto" @click="show = false"> Cancel </Button>

				<Button
					variant="solid"
					@click="() => {
               if(formType == 'addApps') formType = 'siteInput'
               else submitForm()
            }"
					:loading="newSite.loading"
				>
					{{ formType == 'addApps' ? 'Next' : 'Add and deploy site' }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>
