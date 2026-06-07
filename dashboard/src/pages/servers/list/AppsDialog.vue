<script setup lang="ts">
import { ref, reactive, h, defineAsyncComponent } from 'vue'
import {
	Dialog,
	TextInput,
	Button,
	Checkbox,
	createResource,
	createListResource,
} from 'frappe-ui'

import { renderDialog } from '@/utils/components'
import { pollReleasePipelineValidationStatus } from '@/utils/pollReleasePipeline'

interface Props {
	bench: any
}

const show = ref(true)
const props = defineProps<Props>()

const searchQuery = ref('')

const addedApps = reactive([])

const handleAppSelection = (cond, app) => {
	if (cond) addedApps.push(app)
	else addedApps.splice(addedApps.indexOf(app), 1)
}

const err = ref<string | null>(null)

const deployRes = createResource({
	url: 'press.api.bench.deploy_and_update',
	auto: false,
})

const deployInfoRes = createResource({
	url: 'press.api.bench.deploy_information',
	auto: false,
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

		show.value = false
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
		return data.map((app) => {
			app.compatible = app.sources.length > 0
			app.source = app.sources.length > 0 ? app.sources[0] : {}
			return app
		})
	},
	auto: true,

	makeParams() {
		return {
			name: props.bench.name,
			cache: ['benchInstallableApps', props.bench.version],
		}
	},
	initialData: [],
})
</script>

<template>
	<Dialog
		v-model="show"
		:options="{ title: 'Deploy apps to your bench', size:'2xl' }"
	>
		<template #body-content>
			<div class="flex flex-col">
				<TextInput
					placeholder="Search for any Frappe app"
					v-model="searchQuery"
					:debounce="500"
				>
					<template #prefix>
						<lucide-search class="size-4 text-ink-gray-5" />
					</template>
				</TextInput>

				<div class="grid grid-cols-2 gap-4 mt-5">
					<label
						class="p-3 text-sm transition-colors duration-300  border rounded flex gap-2
            has-[:checked]:border-outline-gray-5 hover:border-outline-gray-3"
						v-for="app in installableApps.data"
						:key="app.name"
					>
						<div class="p-2 rounded bg-surface-gray-2 row-span-full h-fit">
							<LucideBox class="size-4" />
						</div>

						<div class=" flex flex-col leading-relaxed overflow-hidden">
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
						class="mt-6 ml-auto"
						@click="submitForm"
						:loading="apiRes.loading"
						:loadingText="`Adding ${addedApps.length} apps`"
					>
						Deploy {{ addedApps.length }} apps
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
