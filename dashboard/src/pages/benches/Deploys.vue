<script setup lang="ts">
import {
	createListResource,
	createDocumentResource,
	Badge,
	Select,
	Button,
	Tooltip,
} from 'frappe-ui'
import { date, duration } from '@/utils/format'
import { defineAsyncComponent, h, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { confirmDialog, renderDialog } from '@/utils/components'
import { useRoute } from 'vue-router'
import { getToastErrorMessage } from '@/utils/toast'
import { pollReleasePipelineValidationStatus } from '@/utils/pollReleasePipeline';
import Scrollbar from '@/components/common/Scrollbar.vue'

interface Props {
	name?: string
}
const props = defineProps<Props>()

const group = createDocumentResource({
	doctype: 'Release Group',
	name: props.name,
	auto: true,
})

const deployBuilds = createListResource({
	doctype: 'Deploy Candidate Build',
	fields: ['name', 'status', 'creation', 'build_duration', 'owner'],
	filters: {
		group: props.name,
		creation: ['<=', '2026-04-21 23:49:24'],
	},
	orderBy: 'creation desc',
})

const pipelines = createListResource({
	doctype: 'Release Pipeline',
	fields: ['name', 'status', 'creation', 'team.user as team'],
	filters: {
		release_group: props.name,
	},
	orderBy: 'creation desc',
})

const badgeThemes = {
	Running: 'blue',
	Success: 'green',
	Failure: 'red',
	Pending: 'yellow',
	Preparing: 'yellow',
}

const statusOptions = [
	'',
	'Draft',
	'Scheduled',
	'Pending',
	'Preparing',
	'Running',
	'Success',
	'Failure',
]

const route = useRoute()
const mode = ref(route.query.pipeline === 'false' ? 'older' : 'newer')

watch(
	mode,
	(x) => {
		if (x === 'newer') {
			pipelines.fetch()
		} else deployBuilds.fetch()
	},
	{ immediate: true },
)

const handleStatusChange = (status: string) => {
	const resObj = mode?.value === 'newer' ? pipelines : deployBuilds
	resObj.filters.status = status
	resObj.reload()
}

function handleDeploy() {
	if (group.doc?.deploy_information?.deploy_in_progress) {
		return toast.error('Deploy is in progress. Please wait for it to complete.')
	}

	if (group.doc?.deploy_information?.update_available) {
		const UpdateReleaseGroupDialog = defineAsyncComponent(
			() => import('@/components/group/UpdateReleaseGroupDialog.vue'),
		)
		renderDialog(
			h(UpdateReleaseGroupDialog, {
				bench: group.name,
				lastDeploy: true,
				onSuccess(candidate: string) {
					group.doc.deploy_information.has_running_release_pipeline = true
					group.doc.deploy_information.update_available = false
					if (candidate) {
						group.doc.deploy_information.last_deploy = { name: candidate }
					}
					pollReleasePipelineValidationStatus(group)
				},
			}),
		)

		return
	}

	return confirmDialog({
		title: 'Deploy without app updates?',
		message:
			'No app updates detected. Changes in dependencies and environment variables will be applied on deploying.',
		onSuccess: ({ hide }: { hide: () => void }) => {
			toast.promise(group.redeploy.submit(), {
				loading: 'Deploying...',
				success: () => {
					hide()
					pipelines.reload()
					deployBuilds.reload()
					return 'Changes Deployed'
				},
				error: (e: Error) => getToastErrorMessage(e),
			})
		},
	})
}
</script>

<template>
	<div class="flex items-center gap-2 mb-3">
		<Button @click="mode = 'newer'" v-if="mode == 'older'">
			<template #icon>
				<LucideChevronLeft class="size-4" />
			</template>
		</Button>

		<div class="font-medium" v-if='mode == "older"'>Older Deploys</div>

		<Select
			:options="statusOptions"
			@update:modelValue="handleStatusChange"
			placeholder="Select Status"
			class="max-w-[130px]"
			:class="mode == 'newer'? 'mr-auto' : 'ml-auto'"
		/>

		<Button @click="mode = 'older'" v-if="mode == 'newer'">
			<LucideHistory class="size-4" />
		</Button>

		<Button
			@click="mode == 'older' ? deployBuilds.reload() : pipelines.reload()"
		>
			<lucide-refresh-ccw class="size-4" />
		</Button>

		<Button @click="handleDeploy" v-if='mode == "older"'>
			<template #prefix> <LucideRocket class="size-4" /></template>
			Deploy
		</Button>
	</div>

	<Scrollbar class="h-[calc(100dvh-300px)] md:h-[calc(100dvh-230px)]">
		<div class="table w-full [&_.table-cell]:p-2">
			<div
				class="bg-surface-gray-2  text-ink-gray-4  sticky top-0 z-10 table-header-group"
			>
				<div class="table-row" role="row">
					<div class="rounded-l table-cell">Deploy</div>
					<div class="table-cell">Status</div>

					<template v-if="mode === 'older'">
						<div class="table-cell">Duration</div>
						<div class="table-cell rounded-r">Deployed By</div>
					</template>

					<div class="table-cell rounded-r" v-else>Team</div>
				</div>
			</div>

			<div class="h-3 invisible">a</div>

			<div class="table-row-group">
				<router-link
					v-for="item in mode == 'older' ? deployBuilds.data : pipelines.data"
					:key="item.name"
					class="hover:bg-surface-gray-1 table-row *:border-b"
					:to="{name: mode=='older' ?'Deploy Candidate':'Release Pipeline', params: {id: item.name,name }}"
					role="row"
				>
					<div class="whitespace-nowrap table-cell hover:rounded-l" role="cell">
						Deploy on {{ date(item.creation) }}
					</div>

					<div class="table-cell" role="cell">
						<Badge :label="item.status" :theme="badgeThemes[item.status]">
							<template #suffix v-if="item.addressable_notification">
								<Tooltip text="Attention required!">
									<LucideAlertCircle class="size-3" />
								</Tooltip>
							</template>
						</Badge>
					</div>

					<template v-if="mode === 'older'">
						<div class="table-cell" role="cell">
							{{ duration(item.build_duration) }}
						</div>
						<div class="table-cell hover:rounded-r" role="cell">
							{{ item.owner }}
						</div>
					</template>

					<div role="cell" class="table-cell" v-else>{{ item.team }}</div>
				</router-link>
			</div>
		</div>
	</Scrollbar>

	<div class="w-full flex">
		<Button
			v-if="mode == 'older'? deployBuilds.hasNextPage : pipelines.hasNextPage "
			class="ml-auto mt-3"
			@click="mode == 'older'? deployBuilds.next() : pipelines.next()"
		>
			Load more
		</Button>
	</div>
</template>
