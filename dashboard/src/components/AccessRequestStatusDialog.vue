<template>
	<Dialog
		v-model="open"
		:options="{
			title: 'Access Status',
			actions: [
				{
					label: 'Request Another',
					variant: 'subtle',
					iconRight: 'arrow-right',
					onClick: () => {
						open = false;
						emit('openRequestDialog');
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base">
				<div class="space-y-2">
					<p><span class="font-medium">Type:</span> {{ props.doctype }}</p>
					<p><span class="font-medium">Resource:</span> {{ props.docname }}</p>
					<p>
						<span class="font-medium">Expiry:</span>
						<Tooltip :text="dayjsLocal(props.access.until).format('LLLL')">
							<span>{{ dayjsLocal(props.access.until).fromNow() }}</span>
						</Tooltip>
					</p>
				</div>
				<div class="rounded-sm border divide-y">
					<div class="grid grid-cols-5 font-medium bg-surface-gray-1 divide-x">
						<div class="col-span-2 py-2 px-3">Permission</div>
						<div class="col-span-1 py-2 px-3">Granted</div>
						<div class="col-span-2 py-2 px-3">Expiry</div>
					</div>
					<div
						v-for="permission in props.access.permissions"
						class="grid grid-cols-5 divide-x"
					>
						<div class="col-span-2 py-2 px-3 font-medium">
							{{ permission.name }}
						</div>
						<div class="col-span-1 py-2 px-3">
							{{ permission.allowed ? 'Yes' : 'No' }}
						</div>
						<div class="col-span-2 py-2 px-3">
							<Tooltip
								v-if="permission.until"
								:text="dayjsLocal(permission.until).format('LLLL')"
							>
								<span>{{ dayjsLocal(permission.until).fromNow() }}</span>
							</Tooltip>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script lang="ts">
type Permission = { name: string; allowed: boolean; until: string | null }

// An active grant, as `press.api.access.status` returns it.
export type Access = { until: string; permissions: Permission[] }
</script>

<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { ref } from 'vue'
import { dayjsLocal } from '../utils/dayjs'

// The caller opens this dialog only when a grant exists.
const props = defineProps<{
	doctype: string
	docname: string
	access: Access
}>()

const emit = defineEmits<{
	openRequestDialog: []
}>()

const open = ref(true)
</script>
