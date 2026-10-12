<script setup lang="ts">
import { Badge, Checkbox, getCachedDocumentResource } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import dayjs from '../../utils/dayjs'
import { bytes } from '../../utils/format'
import { getToastErrorMessage } from '../../utils/toast'
import AlertBanner from '../AlertBanner.vue'

interface LocalBackup {
	file: string
	type: string
	size: number
	modified: string
	download_url: string
}

const props = defineProps<{ site: string }>()
const $site = getCachedDocumentResource('Site', props.site)

const show = ref(true)
const step = ref<'list' | 'confirm'>('list')
const backups = ref<LocalBackup[]>([])
const loaded = ref(false)
const selected = ref<string[]>([])
const acknowledged = ref(false)

const BADGE_THEMES: Record<string, string> = {
	Database: 'blue',
	'Public Files': 'green',
	'Private Files': 'orange',
	'Site Config': 'gray',
}

const selectedBackups = computed(() =>
	backups.value.filter((b) => selected.value.includes(b.file)),
)
const totalSize = computed(() =>
	backups.value.reduce((total, b) => total + b.size, 0),
)
const selectedSize = computed(() =>
	selectedBackups.value.reduce((total, b) => total + b.size, 0),
)
const allSelected = computed(
	() =>
		backups.value.length > 0 && selected.value.length === backups.value.length,
)

function fetchBackups() {
	loaded.value = false
	return $site.getLocalBackups.submit().then((data: LocalBackup[]) => {
		backups.value = data
		selected.value = selected.value.filter((f) =>
			data.some((b) => b.file === f),
		)
		loaded.value = true
	})
}

function toggle(file: string, value: boolean) {
	selected.value = value
		? [...selected.value, file]
		: selected.value.filter((f) => f !== file)
}

function toggleAll(value: boolean) {
	selected.value = value ? backups.value.map((b) => b.file) : []
}

function reviewDelete() {
	acknowledged.value = false
	step.value = 'confirm'
}

function deleteSelected() {
	$site.deleteLocalBackups
		.submit({ files: selected.value })
		.then((result: { deleted: string[]; missing: string[] }) => {
			const count = result.deleted.length
			toast.success(`Deleted ${count} backup${count === 1 ? '' : 's'}`)
			selected.value = []
			step.value = 'list'
			fetchBackups()
		})
		.catch((e: unknown) => {
			toast.error(getToastErrorMessage(e, 'Failed to delete backups'))
		})
}

function relative(modified: string) {
	return dayjs(modified).fromNow()
}

function absolute(modified: string) {
	return dayjs(modified).format('D MMM YYYY, h:mm A')
}

onMounted(fetchBackups)
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: step === 'list' ? 'Local Backups' : 'Delete local backups?',
			size: '4xl',
		}"
	>
		<template #body-content>
			<!-- List of backups on the server -->
			<div v-if="step === 'list'" class="flex flex-col gap-4 text-base">
				<p class="text-p-base text-ink-gray-6">
					Backups stored on the server in
					<code class="text-sm">sites/{{ site }}/private/backups</code>. These
					count towards your site's storage.
				</p>

				<AlertBanner
					type="warning"
					title="Downloading from here only works while you're logged in to the site as a System Manager. Large files use a lot of bandwidth and can fail midway. For reliable downloads, use offsite backups from the Backups tab."
				/>

				<div
					v-if="!loaded && !$site.getLocalBackups.error"
					class="flex justify-center py-8"
				>
					<LoadingIndicator class="h-5 w-5 text-ink-gray-5" />
				</div>
				<ErrorMessage
					v-else-if="$site.getLocalBackups.error"
					:message="$site.getLocalBackups.error"
				/>
				<div
					v-else-if="!backups.length"
					class="rounded border border-dashed border-outline-gray-2 py-8 text-center text-ink-gray-5"
				>
					No backups stored on the server
				</div>

				<div
					v-else
					class="overflow-hidden rounded border border-outline-gray-1"
				>
					<div
						class="grid grid-cols-[1.5rem_minmax(0,1fr)_7rem_5.5rem_7rem_2rem] items-center gap-3 border-b border-outline-gray-1 bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-5"
					>
						<Checkbox
							:modelValue="allSelected"
							@update:modelValue="toggleAll"
						/>
						<span>File</span>
						<span>Type</span>
						<span class="text-right">Size</span>
						<span>Modified</span>
						<span />
					</div>
					<div class="max-h-80 divide-y divide-outline-gray-1 overflow-y-auto">
						<label
							v-for="backup in backups"
							:key="backup.file"
							class="grid cursor-pointer grid-cols-[1.5rem_minmax(0,1fr)_7rem_5.5rem_7rem_2rem] items-center gap-3 px-3 py-2 hover:bg-surface-gray-1"
						>
							<Checkbox
								:modelValue="selected.includes(backup.file)"
								@update:modelValue="(v: boolean) => toggle(backup.file, v)"
							/>
							<span class="truncate font-mono text-sm" :title="backup.file">
								{{ backup.file }}
							</span>
							<span>
								<Badge
									:label="backup.type"
									:theme="BADGE_THEMES[backup.type] || 'gray'"
								/>
							</span>
							<span class="text-right tabular-nums text-ink-gray-7">
								{{ bytes(backup.size) }}
							</span>
							<span class="text-ink-gray-7" :title="absolute(backup.modified)">
								{{ relative(backup.modified) }}
							</span>
							<a
								:href="backup.download_url"
								target="_blank"
								rel="noopener noreferrer"
								class="flex justify-center text-ink-gray-6 hover:text-ink-gray-9"
								title="Download (requires login to the site)"
								@click.stop
							>
								<lucide-download class="size-4" />
							</a>
						</label>
					</div>
				</div>
			</div>

			<!-- Confirmation before deleting -->
			<div v-else class="flex flex-col gap-4 text-base">
				<AlertBanner
					type="error"
					title="Deleted backups can't be recovered. If these are the only copies of your data, for example when the site has no offsite backups, you will have no way to restore the site after data loss."
				/>
				<p class="text-ink-gray-7">
					You're about to permanently delete
					<strong>{{ selectedBackups.length }}</strong>
					backup file{{ selectedBackups.length === 1 ? '' : 's' }}
					({{ bytes(selectedSize) }}) from the server:
				</p>
				<ul
					class="max-h-48 divide-y divide-outline-gray-1 overflow-y-auto rounded border border-outline-gray-1"
				>
					<li
						v-for="backup in selectedBackups"
						:key="backup.file"
						class="flex items-center justify-between gap-3 px-3 py-2"
					>
						<span class="truncate font-mono text-sm" :title="backup.file">
							{{ backup.file }}
						</span>
						<span class="shrink-0 tabular-nums text-ink-gray-6">
							{{ bytes(backup.size) }}
						</span>
					</li>
				</ul>
				<Checkbox
					v-model="acknowledged"
					label="I understand these backups will be permanently deleted and can't be recovered"
				/>
			</div>
		</template>

		<template #actions>
			<div
				v-if="step === 'list'"
				class="flex items-center justify-between gap-2"
			>
				<span class="text-sm text-ink-gray-5">
					<template v-if="selected.length">
						{{ selected.length }}
						selected · {{ bytes(selectedSize) }}
					</template>
					<template v-else-if="backups.length">
						{{ backups.length }}
						file{{ backups.length === 1 ? '' : 's' }}
						· {{ bytes(totalSize) }}
					</template>
				</span>
				<div class="flex gap-2">
					<Button
						label="Refresh"
						:loading="$site.getLocalBackups.loading"
						@click="fetchBackups"
					>
						<template #prefix><lucide-refresh-cw class="size-4" /></template>
					</Button>
					<Button
						variant="solid"
						theme="red"
						:disabled="!selected.length"
						@click="reviewDelete"
					>
						Delete selected
					</Button>
				</div>
			</div>
			<div v-else class="flex justify-end gap-2">
				<Button label="Back" @click="step = 'list'" />
				<Button
					variant="solid"
					theme="red"
					:disabled="!acknowledged"
					:loading="$site.deleteLocalBackups.loading"
					@click="deleteSelected"
				>
					Delete
					{{ selectedBackups.length }}
					backup{{ selectedBackups.length === 1 ? '' : 's' }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>
