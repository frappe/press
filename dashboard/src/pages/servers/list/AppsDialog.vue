<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { Dialog, TextInput, Button, Checkbox, createResource } from 'frappe-ui'
import ServerIcon from './ServerIcon.vue'

interface Props {
	bench: any
  server: any
}

const show = ref(true)
const props = defineProps<Props>()

const searchQuery = ref('')
const addedApps = reactive([])

const emit = defineEmits<{
	deployed: [pipelineId: string]
}>()

const handleAppSelection = (cond, app) => {
  if (cond && !addedApps.includes(app)) addedApps.push(app)
	else addedApps.splice(addedApps.indexOf(app), 1)
}

const err = ref<string | null>(null)

const deployRes = createResource({
	url: 'press.api.bench.deploy_and_update',
	auto: false,
	onSuccess: (data) => {
    emit('deployed', data)
    show.value = false
	},
})

const deployInfoRes = createResource({
	url: 'press.api.bench.deploy_information',
	auto: false,
	onError(e) {
		err.value = e.messages?.join(', ') ?? 'Failed to fetch deploy information'
	},
})

const apiRes = createResource({
	url: 'press.api.bench.add_apps',
	auto: false,
	async onSuccess() {
		const info = await deployInfoRes.submit({ name: props.bench.name })

		const apps = info.apps
			.filter((a) => addedApps.find((x) => x.name === a.name))
			.map((a) => ({
				app: a.name,
				source: a.source,
				release:
					a.releases?.find((r) => r.name === a.next_release && !r.is_yanked)
						?.name ?? a.next_release,
				hash:
					a.releases?.find((r) => r.name === a.next_release && !r.is_yanked)
						?.hash ?? a.next_release_hash,
			}))

		deployRes.submit({
			name: props.bench.name,
			apps,
			sites: [],
			run_will_fail_check: true,
		})
	},
	onError(e) {
		err.value = e.messages?.join(', ') ?? 'Failed'
	},
})

const submitForm = () => {
	const apps = addedApps.map((x) => ({ app: x.app, source: x.source.name }))

	apiRes.submit({
		name: props.bench.name,
		apps: apps,
	})
}

const installableApps = createResource({
	url: 'press.api.bench.all_apps',
	transform(data) {
		const tmp = data.map((app) => {
			app.compatible = app.sources.length > 0
			app.source = app.sources.length > 0 ? app.sources[0] : {}
			return app
		})

		return tmp.filter((app) => app.source?.repository_owner === 'frappe')
	},
	auto: true,
	params: { name: props.bench.name },
	initialData: [],
})

const filteredApps = computed(() => {
	if (!searchQuery.value) return installableApps.data
	return installableApps.data?.filter((app: any) =>
		app.title.toLowerCase().includes(searchQuery.value.toLowerCase()),
	)
})
</script>

<template>
	<Dialog
		v-model="show"
		:options="{ title: 'Deploy apps to your bench', size:'2xl' }"
	>
		<template #body-content>
			<div class="flex gap-2 items-center mb-5 text-sm">
				<LucideBoxes class="size-3.5" /> {{ bench.title }}
				<span class="bg-surface-gray-4 size-1.5 rounded-full mx-1" />

        <ServerIcon :provider="server.provider" />
				<span>{{ server.title }}</span>
			</div>

			<TextInput
				placeholder="Search for any Frappe app"
				v-model="searchQuery"
				class="w-[calc(50%-8px)]"
			>
				<template #prefix>
					<lucide-search class="size-4 text-ink-gray-5" />
				</template>
			</TextInput>
			<span />

			<div
				class="grid grid-cols-2 gap-4 mt-5 overflow-y-auto min-h-[calc(100vh-25rem)] max-h-[calc(100vh-20rem)] content-start"
			>
				<label
					class="py-2.5 p-3 text-xs transition-colors duration-300  border dark:border-outline-gray-2 rounded flex gap-3
            has-[:checked]:border-outline-gray-5 hover:border-outline-gray-3"
					v-for="app in filteredApps"
					:key="app.name"
				>
					<img :src="app.image" class="size-8 rounded" />

					<div class=" flex flex-col leading-relaxed overflow-hidden -mt-0.5">
						<span class="font-medium">{{ app.title }}</span>
						<span class="text-ink-gray-5 truncate">{{ app?.description }}</span>
					</div>

					<Checkbox
						class="ml-auto"
            :modelValue="addedApps.includes(app)"
						@update:modelValue="(x) => handleAppSelection(x, app)"
					/>
				</label>
			</div>

      <p v-if="err" class="text-ink-red-4 text-sm mt-3">{{ err }}</p>

			<div class="flex col-span-full justify-between items-center mt-6">
				<a
					class="flex items-center gap-2 text-ink-gray-5"
					href="https://docs.frappe.io/cloud/installing-an-app#sites-on-private-bench-groups"
				>
					<LucideInfo class="size-4" />
					Looking for Marketplace Apps?
				</a>
				<Button
					variant="solid"
					@click="submitForm"
					:loading="apiRes.loading"
					:loadingText="`Adding ${addedApps.length} apps`"
					:disabled="addedApps.length == 0"
				>
					Deploy {{ addedApps.length != 0 ? addedApps.length : '' }} apps
				</Button>
			</div>
		</template>
	</Dialog>
</template>
