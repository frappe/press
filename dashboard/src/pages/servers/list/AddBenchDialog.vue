<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Dialog, TextInput, Button, createResource } from 'frappe-ui'

interface Props {
	cluster: string
  server: string
}

const show = ref(true)
const props = defineProps<Props>()

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
</script>

<template>
	<Dialog v-model="show" size="lg" :options="{ title: 'Add Bench' }">
		<template #body-content>
			<form class="flex flex-col" @submit.prevent="onSubmit">
				<span class="text-ink-gray-5 mb-2">
					Bench name <span class="text-ink-red-4">*</span>
				</span>

				<TextInput
					placeholder="Enter Bench name"
					v-model="formData.title"
					required
				/>

				<span class="mb-4 mt-5">
					Select version <span class="text-ink-red-4">*</span>
				</span>

				<div class="flex gap-2 items-center flex-wrap">
					<Button
						v-for="version in benchOptions.data?.versions"
						:key="version.name"
						variant="outline"
						@click="
              formData.version = version.name;
              if (err) err = null
            "
						:class="formData.version === version.name ? '!border-outline-gray-5' : ''"
					>
						{{ version.name }}
					</Button>
				</div>

				<span class="text-ink-red-4 mt-5">{{ err }}</span>

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
