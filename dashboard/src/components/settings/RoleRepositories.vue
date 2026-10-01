<template>
	<div class="space-y-4 text-base">
		<div
			v-if="!restricted"
			class="rounded bg-surface-gray-2 px-4 py-3 text-p-sm text-ink-gray-7"
		>
			Repository access restriction is off for this team, so every member can
			use any repository the team's GitHub account can reach. Turn it on from
			the Roles page for this list to take effect.
		</div>
		<div
			v-else-if="adminAccess"
			class="rounded bg-surface-gray-2 px-4 py-3 text-p-sm text-ink-gray-7"
		>
			This is an admin role, so its members can access every repository.
		</div>

		<div
			v-if="repositories.length > 0"
			class="grid grid-cols-3 gap-4 text-base"
		>
			<a
				v-for="repository in repositories"
				:key="`${repository.repository_owner}/${repository.repository}`"
				:href="`https://github.com/${repository.repository_owner}/${repository.repository}`"
				target="_blank"
				class="group flex rounded border px-3.5 py-3 text-sm"
			>
				<div class="flex min-w-0 gap-4">
					<div
						class="m-auto flex size-14 items-center justify-center rounded-lg bg-surface-gray-2 p-3 text-ink-gray-7"
					>
						<FeatherIcon class="size-6" name="github" />
					</div>
					<div class="flex min-w-0 flex-col">
						<span
							class="mb-1 truncate font-medium"
							:title="repository.repository"
						>
							{{ repository.repository }}
						</span>
						<span class="text-ink-gray-5"
							>{{ repository.repository_owner }}</span
						>
					</div>
				</div>
				<Button
					v-if="!disabled"
					icon="trash-2"
					theme="red"
					class="mb-auto ml-auto opacity-0 transition group-hover:opacity-100"
					@click.prevent.stop="removeRepository(repository)"
				/>
			</a>
		</div>
		<div
			v-else
			class="flex justify-center rounded bg-surface-gray-1 p-20 text-sm text-ink-gray-4"
		>
			No repositories allowed for this role
		</div>

		<div v-if="!disabled">
			<Button label="Add Repositories" icon-left="github" @click="openDialog" />
		</div>

		<Dialog
			v-model="open"
			:options="{
				title: 'Add Repositories',
				size: 'lg',
				actions: [
					{
						label: 'Add',
						variant: 'solid',
						disabled: selected.length === 0,
						onClick: () => addRepositories(),
					},
				],
			}"
		>
			<template #body-content>
				<div class="mb-2 flex items-center justify-between text-base">
					<span>Repositories the team's GitHub account can access.</span>
					<Button
						icon="refresh-cw"
						variant="ghost"
						:loading="options.loading"
						@click="options.submit({ refresh: true })"
					/>
				</div>
				<ErrorMessage
					v-if="options.error"
					class="mb-2"
					:message="options.error"
				/>
				<div
					v-else-if="options.data && !options.data.authorized"
					class="mb-2 text-p-sm text-ink-gray-6"
				>
					The team hasn't connected a GitHub account yet. Connect one from the
					"Add App" dialog of a bench first.
				</div>
				<MultiSelect
					v-model="selected"
					:options="repositoryOptions"
					:loading="options.loading"
					placeholder="Select repositories"
				>
					<template #option="{ item }">
						<FeatherIcon
							class="mr-2 size-4"
							:name="item.private ? 'lock' : 'book'"
						/>
						{{ item.label }}
					</template>
				</MultiSelect>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import {
	Button,
	createResource,
	ErrorMessage,
	FeatherIcon,
	MultiSelect,
} from 'frappe-ui'
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'
import { getToastErrorMessage } from '../../utils/toast'

type Repository = { repository_owner: string; repository: string }
type RepositoryOption = { label: string; value: string; private: boolean }

const props = withDefaults(
	defineProps<{
		roleId: string
		repositories?: Array<Repository>
		restricted?: boolean
		adminAccess?: boolean
		disabled?: boolean
		add: (repositories: Array<string>) => Promise<unknown>
		remove: (owner: string, repository: string) => Promise<unknown>
	}>(),
	{
		repositories: () => [],
		restricted: false,
		adminAccess: false,
		disabled: false,
	},
)

const open = ref(false)
const selected = ref<Array<string>>([])

const options = createResource({
	url: 'press.api.client.run_doc_method',
	makeParams: (args?: { refresh?: boolean }) => ({
		dt: 'Press Role',
		dn: props.roleId,
		method: 'repository_options',
		args: { refresh: Boolean(args?.refresh) },
	}),
	transform: (d: { message: unknown }) => d.message,
})

const repositoryOptions = computed<Array<RepositoryOption>>(() => {
	const existing = new Set(
		props.repositories.map((r) =>
			`${r.repository_owner}/${r.repository}`.toLowerCase(),
		),
	)
	return (options.data?.repositories || []).filter(
		(option: RepositoryOption) => !existing.has(option.value.toLowerCase()),
	)
})

const openDialog = () => {
	open.value = true
	if (!options.data && !options.loading) options.submit()
}

// Same as resources: keep the dialog open until the request settles.
const addRepositories = async () => {
	try {
		await props.add(selected.value)
		selected.value = []
		open.value = false
	} catch (error) {
		toast.error(getToastErrorMessage(error))
	}
}

const removeRepository = async (repository: Repository) => {
	try {
		await props.remove(repository.repository_owner, repository.repository)
	} catch (error) {
		toast.error(getToastErrorMessage(error))
	}
}
</script>
