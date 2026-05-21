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

const open = ref(false)
const resourcesToAdd = ref([])

const _resources = createListResource({
	doctype: 'Team Member Resource',
	fields: ['name', 'team', 'user', 'document_type', 'document_name'],
	filters: {
		team: props.team,
		user: props.userId,
	},
})

const sites = createListResource({
	doctype: 'Site',
	fields: ['name'],
	filters: {
		team: props.team,
	},
})

const benches = createListResource({
	doctype: 'Release Group',
	fields: ['name'],
	filters: {
		team: props.team,
	},
})

const servers = createListResource({
	doctype: 'Server',
	fields: ['name'],
	filters: {
		team: props.team,
	},
})

const _options = computed(() => {
	let options = []
	if (sites.data?.length) {
		for (const site of sites.data) {
			options.push({
				label: site.name,
				value: site.name,
				document_type: 'Site',
				document_name: site.name,
			})
		}
		if (benches.data?.length) {
			for (const bench of benches.data) {
				options.push({
					label: bench.name,
					value: bench.name,
					document_type: 'Release Group',
					document_name: bench.name,
				})
			}
		}
	}
	if (servers.data?.length) {
		for (const server of servers.data) {
			options.push({
				label: server.name,
				value: server.name,
				document_type: 'Server',
				document_name: server.name,
			})
		}
	}
	// Remove options that are already selected.
	options = options.filter((o) => {
		return !_resources.data?.some(
			(r) =>
				r.document_type === o.document_type &&
				r.document_name === o.document_name,
		)
	})
	return options
})

const footer = computed(() => {
	let parts = []
	const servers = _resources.data?.filter((r) => r.document_type === 'Server')
	if (servers?.length) {
		parts.push(`${servers.length} Server${servers.length > 1 ? 's' : ''}`)
	}
	const benches = _resources.data?.filter(
		(r) => r.document_type === 'Release Group',
	)
	if (benches?.length) {
		parts.push(
			`${benches.length} Release Group${benches.length > 1 ? 's' : ''}`,
		)
	}
	const sites = _resources.data?.filter((r) => r.document_type === 'Site')
	if (sites?.length) {
		parts.push(`${sites.length} Site${sites.length > 1 ? 's' : ''}`)
	}
	return parts.length ? parts.join(', ') : 'No resources selected'
})

const onAddResources = () => {
	const _r = resourcesToAdd.value
	resourcesToAdd.value = []
	_r.forEach((r) => {
		const resource = _options.value.find((o) => o.value === r)!
		_resources.insert.submit({
			team: props.team,
			user: props.userId,
			document_type: resource.document_type,
			document_name: resource.document_name,
		})
	})
}

watch(
	() => open.value,
	(open) => {
		if (open) {
			_resources.fetch()
			servers.fetch()
			benches.fetch()
			sites.fetch()
		} else {
			resourcesToAdd.value = []
			_resources.setData([])
		}
	},
)
</script>

<template>
	<div class="cursor-pointer flex items-center gap-3" @click="open = true">
		<Tooltip v-if="allServers" text="This user can access all servers">
			<ServerIcon class="h-4 w-4" />
		</Tooltip>
		<Tooltip
			v-if="allReleaseGroups"
			text="This user can access all release groups"
		>
			<ReleaseGroupIcon class="h-4 w-4" />
		</Tooltip>
		<Tooltip v-if="allSites" text="This user can access all sites">
			<SiteIcon class="h-4 w-4" />
		</Tooltip>
		<p>&mdash;</p>
		<Tooltip text="This user has access to these many resources explicitly">
			<p>{{ resourceCount }}</p>
		</Tooltip>
	</div>
	<Dialog v-model="open" :options="{size: '2xl'}">
		<template #body>
			<div class="p-6 text-base space-y-4 font-normal">
				<div class="flex items-center justify-between">
					<div class="text-2xl font-semibold">{{ userName }}'s Resources</div>
					<div class="flex items-center gap-2">
						<Button
							icon-left="refresh-ccw"
							:disabled="_resources.loading"
							@click="_resources.fetch()"
						>
							Refresh
						</Button>
						<Button icon="x" />
					</div>
				</div>
				<p
					class="py-3 px-4 leading-5 rounded border bg-surface-gray-1 border-outline-gray-1 text-ink-gray-8"
				>
					These resources can be accessed by
					<span class="font-medium">{{ userName }}</span>(<span
						class="font-medium"
						>{{ userId }}</span
					>) as a member of this team.
				</p>
				<div class="rounded-sm border divide-y">
					<div
						v-for="resource in _resources.data"
						class="grid grid-cols-3 divide-x"
					>
						<div class="col-span-1 py-2 px-3 font-medium flex items-center">
							{{ resource.document_type }}
						</div>
						<div class="col-span-2 py-1 px-3">
							<div class="flex items-center justify-between">
								<div>{{ resource.document_name }}</div>
								<Dropdown
									:options="[{
										label: 'Remove',
										icon: 'trash',
										onClick: () => _resources.delete.submit(resource.name),
									}]"
									:button="{ icon: 'more-horizontal', label: 'Options', variant: 'ghost' }"
								/>
							</div>
						</div>
					</div>
				</div>
				<div class="flex items-center gap-2">
					<MultiSelect
						v-model="resourcesToAdd"
						:options="_options"
						class="grow"
						placeholder="Search resources..."
					/>
					<Button
						icon-left="plus"
						:disabled="!resourcesToAdd.length"
						@click="() => onAddResources()"
					>
						Add
					</Button>
				</div>
				<Divider />
				<p
					class="py-3 px-4 leading-5 rounded border bg-surface-gray-1 border-outline-gray-1 text-ink-gray-8"
				>
					Checking these boxes will implicitly give access to all resources of
					that type. For example, checking "All Servers" will give access to all
					current and future servers in the team.
				</p>
				<div class="grid grid-cols-3 gap-2">
					<div class="rounded-md border px-3 py-2">
						<Checkbox
							label="All Servers"
							:model-value="allServers"
							@update:model-value="$emit('update', 'all_servers', $event)"
						/>
					</div>
					<div class="rounded-md border px-3 py-2">
						<Checkbox
							label="All Release Groups"
							:model-value="allReleaseGroups"
							@update:model-value="$emit('update', 'all_release_groups', $event)"
						/>
					</div>
					<div class="rounded-md border px-3 py-2">
						<Checkbox
							label="All Sites"
							:model-value="allSites"
							@update:model-value="$emit('update', 'all_sites', $event)"
						/>
					</div>
				</div>
				<Divider />
				<p class="text-center">{{ footer }}</p>
			</div>
		</template>
	</Dialog>
</template>
