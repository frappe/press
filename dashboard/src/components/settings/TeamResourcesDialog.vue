<script setup lang="ts">
import {
	Button,
	Checkbox,
	createListResource,
	Dialog,
	Divider,
	Dropdown,
	MultiSelect,
	Tooltip,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import ReleaseGroupIcon from '~icons/lucide/boxes'
import SiteIcon from '~icons/lucide/panel-top-inactive'
import ServerIcon from '~icons/lucide/server'

const props = defineProps<{
	team: string
	userId: string
	userName: string
	resourceCount: number
	allServers: boolean
	allReleaseGroups: boolean
	allSites: boolean
}>()

const emits = defineEmits<{
	update: [string, boolean]
}>()

// Controls dialog visibility and the list of resources selected to add
const isDialogOpen = ref(false)
const selectedResourcesToAdd = ref([])

// Existing resources assigned to this team member
const teamMemberResources = createListResource({
	doctype: 'Team Member Resource',
	fields: ['name', 'team', 'user', 'document_type', 'document_name'],
	filters: {
		team: props.team,
		user: props.userId,
	},
})

// Available resource pools for the team — fetched on dialog open
const availableSites = createListResource({
	doctype: 'Site',
	fields: ['name'],
	filters: { team: props.team },
})

const availableBenches = createListResource({
	doctype: 'Release Group',
	fields: ['name'],
	filters: { team: props.team },
})

const availableServers = createListResource({
	doctype: 'Server',
	fields: ['name'],
	filters: { team: props.team },
})

/**
 * Builds a flat list of resource options for the MultiSelect,
 * excluding any resources already assigned to the team member.
 */
const availableResourceOptions = computed(() => {
	const allOptions = [
		...(availableSites.data ?? []).map((site) => ({
			label: site.name,
			value: site.name,
			document_type: 'Site',
			document_name: site.name,
		})),
		...(availableBenches.data ?? []).map((bench) => ({
			label: bench.name,
			value: bench.name,
			document_type: 'Release Group',
			document_name: bench.name,
		})),
		...(availableServers.data ?? []).map((server) => ({
			label: server.name,
			value: server.name,
			document_type: 'Server',
			document_name: server.name,
		})),
	]

	// Filter out resources that are already assigned
	return allOptions.filter(
		(option) =>
			!teamMemberResources.data?.some(
				(existing) =>
					existing.document_type === option.document_type &&
					existing.document_name === option.document_name,
			),
	)
})

/**
 * Builds a human-readable summary of assigned resources by type,
 * shown at the bottom of the dialog.
 */
const resourceSummary = computed(() => {
	const counts = [
		{ type: 'Server', label: 'Server' },
		{ type: 'Release Group', label: 'Release Group' },
		{ type: 'Site', label: 'Site' },
	]
		.map(({ type, label }) => {
			const count =
				teamMemberResources.data?.filter((r) => r.document_type === type)
					.length ?? 0
			return count > 0 ? `${count} ${label}${count > 1 ? 's' : ''}` : null
		})
		.filter(Boolean)

	return counts.length ? counts.join(', ') : 'No resources selected'
})

// Submits inserts for each selected resource, then shows a toast on completion
const onAddResources = () => {
	const pending = selectedResourcesToAdd.value
	selectedResourcesToAdd.value = []

	const insertPromises = pending.map((value) => {
		const resource = availableResourceOptions.value.find(
			(o) => o.value === value,
		)!
		return teamMemberResources.insert.submit({
			team: props.team,
			user: props.userId,
			document_type: resource.document_type,
			document_name: resource.document_name,
		})
	})

	Promise.all(insertPromises).then(() => {
		toast.success(
			`${pending.length} resource${pending.length > 1 ? 's' : ''} added successfully`,
		)
	})
}

// Removes a single resource and notifies the user
const onRemoveResource = (resourceName: string, documentName: string) => {
	teamMemberResources.delete.submit(resourceName).then(() => {
		toast.success(`Removed ${documentName} from resources`)
	})
}

// Fetch all required data when dialog opens; reset state when it closes
watch(
	() => isDialogOpen.value,
	(open) => {
		if (open) {
			teamMemberResources.fetch()
			availableServers.fetch()
			availableBenches.fetch()
			availableSites.fetch()
		} else {
			selectedResourcesToAdd.value = []
			teamMemberResources.setData([])
		}
	},
)
</script>

<template>
	<!-- Trigger row: shows icons for implicit access + explicit resource count -->
	<div
		class="cursor-pointer flex items-center gap-1 max-w-[160px] min-w-0 overflow-hidden whitespace-nowrap"
		:title="`${allServers ? 'All Servers, ' : ''}${allReleaseGroups ? 'All Release Groups, ' : ''}${allSites ? 'All Sites, ' : ''}${resourceCount} explicit resource${resourceCount !== 1 ? 's' : ''}`"
		@click="isDialogOpen = true"
	>
		<Tooltip v-if="allServers" text="This user can access all servers">
			<ServerIcon class="h-4 w-4 shrink-0" />
		</Tooltip>
		<Tooltip
			v-if="allReleaseGroups"
			text="This user can access all release groups"
		>
			<ReleaseGroupIcon class="h-4 w-4 shrink-0" />
		</Tooltip>
		<Tooltip v-if="allSites" text="This user can access all sites">
			<SiteIcon class="h-4 w-4 shrink-0" />
		</Tooltip>
		<span class="shrink-0">&mdash;</span>
		<Tooltip text="This user has access to these many resources explicitly">
			<span class="truncate min-w-[2ch]">{{ resourceCount }}</span>
		</Tooltip>
	</div>

	<Dialog v-model="isDialogOpen" :options="{ size: '2xl' }">
		<template #body>
			<div class="p-6 text-base space-y-4 font-normal">
				<!-- Header -->
				<div class="flex items-center justify-between">
					<div class="text-2xl font-semibold">{{ userName }}'s Resources</div>
					<div class="flex items-center gap-2">
						<Button
							icon-left="refresh-ccw"
							:disabled="teamMemberResources.loading"
							@click="teamMemberResources.fetch()"
						>
							Refresh
						</Button>
						<Button icon="x" @click="isDialogOpen = false" />
					</div>
				</div>

				<!-- Context banner -->
				<p
					class="py-3 px-4 leading-5 rounded border bg-surface-gray-1 border-outline-gray-1 text-ink-gray-8"
				>
					These resources can be accessed by
					<span class="font-medium">{{ userName }}</span>(<span
						class="font-medium"
						>{{ userId }}</span
					>) as a member of this team.
				</p>

				<!-- Resource list -->
				<div
					v-if="teamMemberResources.data?.length"
					class="rounded-sm border divide-y"
				>
					<div
						v-for="resource in teamMemberResources.data"
						:key="resource.name"
						class="grid grid-cols-3 divide-x"
					>
						<div class="col-span-1 py-2 px-3 font-medium flex items-center">
							{{ resource.document_type }}
						</div>
						<div class="col-span-2 py-1 px-3 min-w-0">
							<div class="flex items-center justify-between overflow-hidden">
								<div class="truncate">{{ resource.document_name }}</div>
								<Dropdown
									:options="[
										{
											label: 'Remove',
											icon: 'trash',
											onClick: () =>
												onRemoveResource(
													resource.name,
													resource.document_name,
												),
										},
									]"
									:button="{
										icon: 'more-horizontal',
										label: 'Options',
										variant: 'ghost',
									}"
								/>
							</div>
						</div>
					</div>
				</div>

				<!-- Empty state -->
				<div
					v-else
					class="rounded-sm border py-10 flex flex-col items-center justify-center gap-2 text-ink-gray-5"
				>
					<ServerIcon class="h-6 w-6" />
					<p class="text-sm">No resources have been added yet.</p>
				</div>

				<!-- Add resources -->
				<div class="flex items-center gap-2">
					<div class="min-w-0 overflow-hidden flex-1">
						<MultiSelect
							v-model="selectedResourcesToAdd"
							:options="availableResourceOptions"
							class="w-full"
							placeholder="Search resources..."
						/>
					</div>
					<Button
						icon-left="plus"
						:disabled="!selectedResourcesToAdd.length"
						@click="onAddResources"
					>
						Add
					</Button>
				</div>

				<Divider />

				<!-- Implicit access toggles -->
				<p
					class="py-3 px-4 leading-5 rounded border bg-surface-gray-1 border-outline-gray-1 text-ink-gray-8"
				>
					Checking these boxes will implicitly give access to all resources of
					that type. For example, checking "Servers" will give access to all
					current and future servers in the team.
				</p>
				<div class="grid grid-cols-3 gap-2">
					<div class="flex items-center gap-2 rounded-md border px-3 py-2">
						<ServerIcon class="size-4" />
						<Checkbox
							label="Servers"
							:model-value="allServers"
							@update:model-value="$emit('update', 'all_servers', $event)"
						/>
					</div>
					<div class="flex items-center gap-2 rounded-md border px-3 py-2">
						<ReleaseGroupIcon class="size-4" />
						<Checkbox
							label="Release Groups"
							:model-value="allReleaseGroups"
							@update:model-value="$emit('update', 'all_release_groups', $event)"
						/>
					</div>
					<div class="flex items-center gap-2 rounded-md border px-3 py-2">
						<SiteIcon class="size-4" />
						<Checkbox
							label="Sites"
							:model-value="allSites"
							@update:model-value="$emit('update', 'all_sites', $event)"
						/>
					</div>
				</div>

				<Divider />

				<!-- Summary footer -->
				<p class="text-center">{{ resourceSummary }}</p>
			</div>
		</template>
	</Dialog>
</template>
