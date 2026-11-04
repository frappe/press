<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Authorize backup access',
			actions: canApprove
				? [
						{
							label: 'Approve request',
							variant: 'solid',
							loading: approve.loading,
							onClick: () => approve.submit(),
						},
					]
				: hasNoAccess
					? [{ label: 'Close', onClick: () => (showDialog = false) }]
					: [],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<div v-if="hasNoAccess" class="space-y-1">
					<p class="text-base font-medium text-ink-gray-9">
						You don't have access to allow this request
					</p>
					<p class="text-p-base text-ink-gray-6">
						Ask the owner of the site to approve it.
					</p>
				</div>
				<ErrorMessage v-else :message="request.error" />
				<template v-if="request.data">
					<p class="text-p-base text-ink-gray-7">
						Authorize Pilot to access the mentioned site's backups for
						restoration purposes. Once approved, this authorization will stay
						valid for the next 12 hours.
						<br />
						<br />
						Approve only if you have started this request from Pilot.
					</p>
					<div
						class="divide-y divide-outline-gray-1 rounded border border-outline-gray-1 text-base"
					>
						<div
							v-for="row in details"
							:key="row.label"
							class="flex justify-between gap-4 px-3 py-2"
						>
							<span class="text-ink-gray-5">{{ row.label }}</span>
							<span class="truncate font-medium text-ink-gray-8">
								{{ row.value }}
							</span>
						</div>
					</div>
					<AlertBanner
						v-if="!canApprove"
						:title="`This request is ${request.data.is_expired ? 'expired' : request.data.status.toLowerCase()}. Start again from Pilot.`"
						type="warning"
						:showIcon="false"
					/>
					<template v-else>
						<FormControl
							label="Pass code shown in Pilot"
							placeholder="K7QM2XPA"
							v-model="code"
							maxlength="8"
							autocomplete="off"
							@keydown.enter="approve.submit()"
						/>
						<ErrorMessage :message="approve.error" />
					</template>
				</template>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { createResource, ErrorMessage, FormControl } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { dayjsLocal } from '../../utils/dayjs'
import AlertBanner from '../AlertBanner.vue'

const props = defineProps<{ requestName: string }>()

const route = useRoute()
const router = useRouter()
const showDialog = defineModel<boolean>({ default: true })
const code = ref('')

const request = createResource({
	url: 'press.api.v1_migration.get_request',
	params: { name: props.requestName },
	auto: true,
})

const canApprove = computed(
	() => request.data?.status === 'Pending' && !request.data?.is_expired,
)

const hasNoAccess = computed(
	() => request.error?.exc_type === 'PermissionError',
)

const details = computed(() => [
	{ label: 'Site', value: request.data.site },
	{
		label: 'Requested',
		value: dayjsLocal(request.data.creation).format('D MMM YYYY, h:mm A'),
	},
	{ label: 'IP Address', value: request.data.requester_ip },
])

const approve = createResource({
	url: 'press.api.v1_migration.approve_request',
	makeParams: () => ({
		name: props.requestName,
		code: code.value.trim().toUpperCase(),
	}),
	onSuccess() {
		toast.success('Pilot can now access the backups.')
		showDialog.value = false
	},
	onError() {
		request.reload()
	},
})

watch(showDialog, (isOpen) => {
	if (isOpen) return
	const { 'v1-migration': _, ...query } = route.query
	router.replace({ query })
})
</script>
