<template>
	<div class="p-5">
		<Button :route="{ name: 'Site Detail Updates' }">
			<template #prefix>
				<lucide-arrow-left class="inline-block h-4 w-4" />
			</template>
			All Updates
		</Button>

		<AlertBanner
			v-if="notification"
			class="mt-3"
			:title="notification.message"
			type="warning"
		/>

		<div class="mt-3">
			<div class="flex w-full items-center">
				<h2 class="text-xl-medium text-ink-gray-9">
					Update Site {{ siteUpdate.deploy_type }}
				</h2>
				<Badge class="ml-2" :label="siteUpdate.status" />
				<div class="ml-auto space-x-2">
					<Button
						@click="$resources.siteUpdate.reload()"
						:loading="$resources.siteUpdate.loading"
					>
						<template #icon>
							<lucide-refresh-ccw class="h-4 w-4" />
						</template>
					</Button>
					<Dropdown :options="dropdownOptions">
						<template v-slot="{ open }">
							<Button>
								<template #icon>
									<lucide-more-horizontal class="h-4 w-4" />
								</template>
							</Button>
						</template>
					</Dropdown>
				</div>
			</div>
			<div>
				<div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
					<div>
						<div class="text-sm-medium text-ink-gray-5">Creation</div>
						<div class="mt-2 text-sm text-ink-gray-9">
							{{ $format.date(siteUpdate.creation, 'lll') }}
						</div>
					</div>
					<div>
						<div class="text-sm-medium text-ink-gray-5">Creator</div>
						<div class="mt-2 text-sm text-ink-gray-9">
							{{ siteUpdate.owner }}
						</div>
					</div>
					<div>
						<div class="text-sm-medium text-ink-gray-5">Duration</div>
						<div class="mt-2 text-sm text-ink-gray-9">
							{{ siteUpdate.update_duration
									? this.format_seconds(siteUpdate.update_duration)
									: '-' }}
						</div>
					</div>
					<div>
						<div class="text-sm-medium text-ink-gray-5">Start</div>
						<div class="mt-2 text-sm text-ink-gray-9">
							{{ $format.date(siteUpdate.update_start, 'lll') }}
						</div>
					</div>
					<div>
						<div class="text-sm-medium text-ink-gray-5">End</div>
						<div class="mt-2 text-sm text-ink-gray-9">
							{{ siteUpdate.update_end
									? $format.date(siteUpdate.update_end, 'lll')
									: '-' }}
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Build Steps -->
		<div class="mt-8 space-y-4">
			<JobStep v-for="step in steps" :step="step" :key="step.name" />
		</div>
	</div>
</template>
<script>
import AlertAddressableError from '../components/AlertAddressableError.vue'
import AlertBanner from '../components/AlertBanner.vue'
import JobStep from '../components/JobStep.vue'

export default {
	name: 'SiteUpdate',
	props: ['id'],
	components: {
		JobStep,
		AlertBanner,
		AlertAddressableError,
	},
	resources: {
		notification() {
			if (!this.id) return
			return {
				type: 'list',
				doctype: 'Press Notification',
				auto: true,
				fields: ['message', 'name'],
				filters: {
					document_type: 'Site Update',
					document_name: this.id,
				},
				limit: 1,
				orderBy: 'creation desc',
			}
		},
		siteUpdate() {
			if (!this.id) return
			return {
				type: 'document',
				doctype: 'Site Update',
				name: this.id,
				auto: true,
				transform: (record) => {
					record.steps = record.steps.map((step) => {
						return {
							name: step.name,
							title: `${step.stage} - ${step.title}`,
							output: step.output || 'No Output',
							status: step.status,
							isOpen: false,
						}
					})
				},
				onSuccess: (data) => {
					if (
						!['Success', 'Failure', 'Recovered', 'Fatal', 'Cancelled'].includes(
							data.status,
						)
					) {
						setTimeout(() => {
							this.$resources.siteUpdate.reload()
						}, 5000)
					}
				},
			}
		},
	},
	computed: {
		siteUpdate() {
			return this.$resources.siteUpdate?.doc ?? {}
		},
		notification() {
			return this.$resources.notification?.data?.[0] ?? null
		},
		steps() {
			return this.$resources.siteUpdate?.doc?.steps || []
		},
		dropdownOptions() {
			return [
				{
					label: 'View in Desk',
					icon: 'lucide-external-link',
					condition: () => this.$team.doc?.is_desk_user,
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/site-update/${this.id}`,
							'_blank',
						)
					},
				},
			].filter((option) => option.condition?.() ?? true)
		},
	},
	methods: {
		format_seconds(seconds) {
			if (seconds === null) {
				return '-'
			}
			if (seconds < 60) {
				return `${Math.ceil(seconds)}s`
			}
			const minutes = Math.floor(seconds / 60)
			const remainingSeconds = Math.ceil(seconds % 60)
			return `${minutes}m ${remainingSeconds}s`
		},
	},
}
</script>
