<template>
	<div class="space-y-4">
		<div
			class="grid grid-cols-3 gap-4 text-base"
			v-if="resources && resources.length > 0"
		>
			<component
				:is="resource.document_type === REPOSITORY ? 'a' : RouterLink"
				v-for="resource in resources"
				v-bind="linkAttributes(resource)"
				class="text-sm border rounded flex group py-3 px-3.5"
			>
				<div class="flex gap-4 rounded transition min-w-0">
					<div
						class="m-auto size-14 rounded-lg flex items-center justify-center p-3"
						:class="colorClasses[resource.document_type]"
					>
						<FeatherIcon class="size-6" :name="icons[resource.document_type]" />
					</div>

					<div class="flex flex-col min-w-0">
						<span
							v-if="resource.document_type !== 'Site'"
							class="truncate font-medium mb-1"
							:title="resource.document_title"
						>
							{{ resource.document_title }}
						</span>

						<span class="mb-2 text-ink-gray-5"
							>{{ resource.document_name }}</span
						>
						<span class="text-ink-gray-5 text-xs"
							>{{ typeLabels[resource.document_type] ?? resource.document_type }}</span
						>
					</div>
				</div>
				<Button
					icon="trash-2"
					theme="red"
					class="opacity-0 group-hover:opacity-100 transition mb-auto ml-auto"
					@click.prevent.stop="
						removeResource(resource.document_type, resource.document_name)
					"
				/>
			</component>
		</div>

		<div
			v-else
			class="text-ink-gray-4 text-sm p-20 rounded flex bg-surface-gray-1 justify-center"
		>
			No resources to show
		</div>
		<div>
			<Button label="Include" icon-left="globe" @click="openIncludeDialog" />
		</div>
		<Dialog
			v-model="open"
			:options="{
				title: 'Include',
				size: 'lg',
				actions: [
					{
						label: 'Submit',
						variant: 'solid',
						onClick: () => includeResources(),
					},
				],
			}"
		>
			<template #body-content>
				<div class="mb-2 text-base">Include a resource in this role.</div>
				<div v-if="repositoriesLoading" class="mb-2 text-sm text-ink-gray-5">
					Loading GitHub repositories...
				</div>
				<MultiSelect
					:options="resourcesToIncludeOptions"
					:model-value="
						resourcesToIncludeModel.map((item) => item.document_name)
					"
					@update:model-value="
						resourcesToIncludeModel = resourcesToIncludeOptions.filter(
							(option) => $event.includes(option.value),
						)
					"
					placeholder="Select resources"
				>
					<template #option="{ item }">
						<FeatherIcon
							class="size-4 mr-2"
							:name="icons[item.document_type]"
						/>
						{{ item.label }}
					</template>
				</MultiSelect>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { Button, FeatherIcon, MultiSelect } from 'frappe-ui'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { getTeam } from '../../data/team'
import { getToastErrorMessage } from '../../utils/toast'
import { fetchTeamRepositories, REPOSITORY, teamResources } from './data'

type Resource = { document_type: string; document_name: string }

const props = withDefaults(
	defineProps<{
		resources?: Array<any>
		include: (resources: Array<Resource>) => Promise<unknown>
		remove: (documentType: string, documentName: string) => Promise<unknown>
	}>(),
	{
		resources: () => [],
	},
)

const team = getTeam()

const colorClasses = {
	'Release Group': 'bg-surface-blue-2 text-ink-blue-2',
	Server: 'bg-surface-amber-1 text-ink-amber-2',
	Site: 'bg-surface-green-2 text-ink-green-2',
	[REPOSITORY]: 'bg-surface-gray-2 text-ink-gray-7',
}

const icons = {
	'Release Group': 'package',
	Server: 'server',
	Site: 'globe',
	[REPOSITORY]: 'github',
}

const typeLabels = {
	'Release Group': 'Bench',
	[REPOSITORY]: 'Repository',
}

const open = ref(false)
const repositories = ref<Array<Resource & { label: string; value: string }>>([])
const repositoriesLoading = ref(false)

// Repositories come from GitHub, so they load when the dialog first opens
const openIncludeDialog = async () => {
	open.value = true
	const loaded = repositories.value.length || repositoriesLoading.value
	if (!team.doc?.github_installations_enabled || loaded) {
		return
	}
	repositoriesLoading.value = true
	try {
		repositories.value = await fetchTeamRepositories()
	} finally {
		repositoriesLoading.value = false
	}
}

const resourcesToIncludeModel = ref<Array<Resource>>([])

// The dialog stays open until the request settles. Closing it right away made
// a slow request look like a no-op, and the retries that followed raced each
// other on the server.
const includeResources = async () => {
	try {
		await props.include(resourcesToIncludeModel.value)
		resourcesToIncludeModel.value = []
		open.value = false
	} catch (error) {
		toast.error(getToastErrorMessage(error))
	}
}

const removeResource = async (documentType: string, documentName: string) => {
	try {
		await props.remove(documentType, documentName)
	} catch (error) {
		toast.error(getToastErrorMessage(error))
	}
}

const resourcesToIncludeOptions = computed(() => {
	return [...teamResources.value, ...repositories.value].filter(
		(resource) =>
			!props.resources?.some(
				(r) =>
					r.document_type === resource.document_type &&
					r.document_name === resource.document_name,
			),
	)
})

const linkAttributes = (resource: any) => {
	if (resource.document_type === REPOSITORY) {
		const href = `https://github.com/${resource.document_name}`
		return { href, target: '_blank', rel: 'noopener noreferrer' }
	}
	return { to: toLink(resource) }
}

const toLink = (resource: any) => {
	if (resource.document_type === 'Site') {
		return {
			name: 'Site Detail',
			params: {
				name: resource.document_name,
			},
		}
	} else if (resource.document_type === 'Server') {
		return {
			name: 'Server Detail',
			params: {
				name: resource.document_name,
			},
		}
	} else if (resource.document_type === 'Release Group') {
		return {
			name: 'Release Group Detail',
			params: {
				name: resource.document_name,
			},
		}
	}
	return '#'
}
</script>
