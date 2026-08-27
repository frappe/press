<template>
	<div class="p-5" v-if="job">
		<AlertAddressableError
			v-if="error"
			class="mb-5"
			:name="error.name"
			:title="error.title"
			@done="$resources.errors.reload()"
		/>
		<Button
			:route="{
				name:
					object.doctype === 'Site'
						? 'Site Jobs'
						: `${object.doctype} Detail Jobs`,
			}"
		>
			<template #prefix>
				<lucide-arrow-left class="inline-block h-4 w-4" />
			</template>
			All jobs
		</Button>

		<div class="mt-3">
			<div>
				<div class="flex items-center">
					<h2 class="text-lg font-medium text-ink-gray-9">
						{{ job.job_type }}
					</h2>
					<Badge class="ml-2" :label="job.status" />
					<div class="ml-auto flex items-center space-x-2">
						<Button
							@click="$resources.job.reload()"
							:loading="$resources.job.get.loading"
						>
							<template #icon>
								<lucide-refresh-ccw class="h-4 w-4" />
							</template>
						</Button>
						<Button
							v-if="canCancel"
							@click="confirmCancel"
							:loading="$resources.job.cancelJob.loading"
							theme="red"
						>
							Cancel Job
						</Button>
						<Dropdown v-if="dropdownOptions.length" :options="dropdownOptions">
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
					<div
						class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5"
					>
						<div>
							<div class="text-sm font-medium text-ink-gray-5">Creation</div>
							<div class="mt-2 text-sm text-ink-gray-9">
								{{ $format.date(job.creation, 'lll') }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-ink-gray-5">Creator</div>
							<div class="mt-2 text-sm text-ink-gray-9">
								{{ job.owner }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-ink-gray-5">Duration</div>
							<div class="mt-2 text-sm text-ink-gray-9">
								{{ job.end ? $format.duration(job.duration) : '-' }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-ink-gray-5">Start</div>
							<div class="mt-2 text-sm text-ink-gray-9">
								{{ $format.date(job.start, 'lll') }}
							</div>
						</div>
						<div>
							<div class="text-sm font-medium text-ink-gray-5">End</div>
							<div class="mt-2 text-sm text-ink-gray-9">
								{{ job.end ? $format.date(job.end, 'lll') : '-' }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="mt-8 space-y-4">
				<JobStep v-for="step in job.steps" :step="step" :key="step.name" />
			</div>
		</div>
	</div>
</template>
<script>
import { FeatherIcon, Tooltip } from 'frappe-ui'
import { toast } from 'vue-sonner'
import AlertAddressableError from '../components/AlertAddressableError.vue'
import JobStep from '../components/JobStep.vue'
import { getObject } from '../objects'
import { confirmDialog } from '../utils/components'
import { duration } from '../utils/format'
import { getToastErrorMessage } from '../utils/toast'

// Keep in sync with DASHBOARD_CANCELLABLE_JOB_TYPES in agent_job.py
const cancellableJobTypes = [
	'Restore Site',
	'New Site from Backup',
	'Backup Site',
	'Update Site Migrate',
]

export default {
	name: 'JobPage',
	props: ['id', 'objectType'],
	components: { Tooltip, FeatherIcon, JobStep, AlertAddressableError },
	resources: {
		job() {
			return {
				type: 'document',
				doctype: 'Agent Job',
				name: this.id,
				whitelistedMethods: { cancelJob: 'cancel_job' },
				transform(job) {
					for (let step of job.steps) {
						step.title = step.step_name
						step.duration = duration(step.duration)
						step.isOpen =
							this.job?.steps?.find((s) => s.name === step.name)?.isOpen ||
							false
					}

					// on delivery failure, there'll be no output for any step
					// so show the job output (error) in the first step
					if (['Undelivered', 'Delivery Failure'].includes(job.status)) {
						job.steps[0].output = job.output
					}

					return job
				},
				onSuccess() {
					this.lastLoaded = Date.now()
				},
			}
		},
		// a site update that skipped backups has nothing to recover from,
		// so its migrate job can't be cancelled
		siteUpdate() {
			return {
				type: 'list',
				doctype: 'Site Update',
				auto: this.job?.job_type === 'Update Site Migrate',
				fields: ['skipped_backups'],
				filters: { update_job: this.id },
				limit: 1,
			}
		},
		errors() {
			return {
				type: 'list',
				cache: ['Press Notification', 'Error', 'Agent Job', this.id],
				doctype: 'Press Notification',
				auto: true,
				fields: ['title', 'name'],
				filters: {
					document_type: 'Agent Job',
					document_name: this.id,
					is_actionable: true,
					class: 'Error',
				},
				limit: 1,
				orderBy: 'creation desc',
			}
		},
	},
	computed: {
		object() {
			return getObject(this.objectType)
		},
		job() {
			return this.$resources.job.doc
		},
		error() {
			return this.$resources.errors?.data?.[0] ?? null
		},
		canCancel() {
			if (!['Pending', 'Running'].includes(this.job.status)) return false
			if (!cancellableJobTypes.includes(this.job.job_type)) return false
			if (this.job.job_type !== 'Update Site Migrate') return true

			// wait for the site update, so the button doesn't flash for an
			// update that turns out to have skipped its backups
			const siteUpdate = this.$resources.siteUpdate.data?.[0]
			return Boolean(siteUpdate) && !siteUpdate.skipped_backups
		},
		dropdownOptions() {
			return [
				{
					label: 'View in Desk',
					icon: 'external-link',
					condition: () => this.$team?.doc?.is_desk_user,
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/agent-job/${this.id}`,
							'_blank',
						)
					},
				},
			].filter((option) => option.condition?.() ?? true)
		},
	},
	mounted() {
		this.$socket.emit('doc_subscribe', 'Agent Job', this.id)
		this.$socket.on('agent_job_update', (data) => {
			if (data.id === this.id) {
				data.steps = data.steps.map((step) => {
					step.title = step.step_name
					step.duration = duration(step.duration)
					step.isOpen =
						this.job?.steps?.find((s) => s.name === step.name)?.isOpen || false
					return step
				})

				this.$resources.job.doc = {
					...this.$resources.job.doc,
					...data,
				}
			}
		})
		// reload job every minute, in case socket is not working
		this.reloadInterval = setInterval(() => {
			this.reload()
		}, 1000 * 60)
	},
	beforeUnmount() {
		this.$socket.emit('doc_unsubscribe', 'Agent Job', this.id)
		this.$socket.off('agent_job_update')
		clearInterval(this.reloadInterval)
	},
	methods: {
		confirmCancel() {
			const warning =
				this.job.job_type === 'Update Site Migrate'
					? '<br><br>The update will be marked as failed and a recovery job will restore the backup and roll the site back to the previous bench.'
					: ''

			confirmDialog({
				title: 'Cancel Job',
				message: `Are you sure you want to cancel this <b>${this.job.job_type}</b> job?<br><br>It will stop midway and <b>can't be resumed</b>.${warning}`,
				primaryAction: {
					label: 'Cancel Job',
					variant: 'solid',
					theme: 'red',
					onClick: ({ hide }) => {
						toast.promise(this.$resources.job.cancelJob.submit(), {
							loading: 'Cancelling job...',
							success: () => {
								hide()
								return 'Job will be cancelled shortly'
							},
							error: (e) => getToastErrorMessage(e, 'Failed to cancel job'),
						})
					},
				},
			})
		},
		reload() {
			if (
				!this.$resources.job.loading &&
				// reload if job was loaded more than 5 seconds ago
				Date.now() - this.lastLoaded > 5000
			) {
				this.$resources.job.reload()
			}
		},
	},
}
</script>
