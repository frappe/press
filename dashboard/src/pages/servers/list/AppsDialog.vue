<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Dialog, TextInput, Button, Checkbox, createResource } from 'frappe-ui'
import '@/styles/checkbox.css'

interface Props {
	cluster: string
	server: string
	onSuccess: () => void
}

const show = ref(true)
const props = defineProps<Props>()

const searchQuery = ref('')

const benchOptions = createResource({
	url: 'press.api.bench.options',
	auto: true,
})

const formData = reactive({
	title: '',
	version: null as string | null,
})

const err = ref<string | null>(null)

function getAppsToInstall() {
	const version = benchOptions.data?.versions?.find(
		(v: any) => v.name === formData.version,
	)

	if (!version) return []

	const tmp = version.apps.filter((app: any) => app.name === 'frappe')

	return tmp.map((app: any) => ({
		name: app.name,
		source: app.source.name,
	}))
}

const createBench = createResource({
	url: 'press.api.bench.new',
	onSuccess() {
		show.value = false
		props.onSuccess()
	},
})

const onSubmit = () => {
	if (!formData.version) {
		err.value = 'Please select a version'
		return
	}

	createBench.submit({
		bench: {
			title: formData.title,
			version: formData.version,
			cluster: props.cluster,
			saas_app: null,
			apps: getAppsToInstall(),
			server: props.server,
		},
	})
}

const dummy = {
	title: 'Framework',
	source: 'frappe',
	description: 'Framework for building web apps',
	image: 'https://frappe.io/assets/frappe-framework-logo.svg',
}
</script>

<template>
	<Dialog
		v-model="show"
		:options="{ title: 'Deploy apps to your bench', size:'2xl' }"
	>
		<template #body-content>
			<form class="flex flex-col" @submit.prevent="onSubmit">
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
						class="p-3 transition-colors duration-300  border rounded flex gap-2 has-[:checked]:border-outline-gray-5"
						v-for="x in 4"
					>
						<div class="p-2 rounded bg-surface-gray-2 row-span-full h-fit">
							<LucideBox class="size-4" />
						</div>

						<div class=" flex flex-col leading-relaxed">
							<span class="font-medium">{{ dummy.title }}</span>
							<span class="text-ink-gray-5 whitespace-nowrap"
								>{{ dummy.description }}</span
							>
						</div>

						<Checkbox />
					</label>
				</div>

				<div class="flex">
					<Button
						variant="solid"
						class="mt-6 ml-auto"
						type="submit"
						:loading="createBench.loading"
					>
						Add Bench
					</Button>
				</div>
			</form>
		</template>
	</Dialog>
</template>
