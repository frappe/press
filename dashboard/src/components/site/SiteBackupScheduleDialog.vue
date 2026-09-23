<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Backup Schedule',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					disabled: !loaded,
					loading: saving,
					onClick: save,
				},
			],
		}"
	>
		<template #body-content>
			<div v-if="!loaded" class="flex justify-center py-8">
				<ErrorMessage
					v-if="$site.getBackupSchedule.error"
					:message="$site.getBackupSchedule.error"
				/>
				<LoadingIndicator v-else class="h-5 w-5 text-ink-gray-5" />
			</div>

			<div v-else class="flex flex-col gap-5">
				<Switch
					v-if="canSetOffsite"
					v-model="offsite"
					label="Offsite backups"
					:description="
						offsite
							? 'A copy of the daily backup goes to our offsite storage'
							: 'Backups stay on the server, and your bench drops them within a day'
					"
				/>

				<p v-if="managed" class="text-base leading-5 text-ink-gray-7">
					Your site backs up at {{ managedTimes }} every day. We set that up for
					you — write to support to change it.
				</p>

				<template v-else-if="canSetTime">
					<Switch
						v-model="custom"
						label="Backup site at custom time"
						:description="
							custom
								? 'Backups run once a day, at the hour below'
								: 'Backups run every 6 hours, whenever that falls'
						"
					/>

					<!-- Laid out like the Switch above: label and description left, control right -->
					<div v-if="custom" class="flex items-center justify-between">
						<div class="flex flex-col gap-1">
							<span
								class="text-base font-medium leading-normal text-ink-gray-8"
							>
								Backup time
							</span>
							<span class="text-p-sm text-ink-gray-7">
								Starts within this hour ({{ timezone }})
							</span>
						</div>
						<FormControl
							class="w-32"
							type="select"
							variant="outline"
							:options="hourOptions"
							v-model="hour"
						/>
					</div>
				</template>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource, Switch } from 'frappe-ui'
import { toast } from 'vue-sonner'
import dayjs, { timeLocal, timeServer } from '../../utils/dayjs'
import { getToastErrorMessage } from '../../utils/toast'

// Backups fire on the hour, so offering minutes would promise precision the
// scheduler doesn't have.
const HOURS = Array.from({ length: 24 }, (_, hour) => ({
	label: dayjs().hour(hour).minute(0).format('h:mm A'),
	value: String(hour).padStart(2, '0'),
}))

export default {
	props: ['site'],
	components: { Switch },
	data() {
		return {
			show: true,
			offsite: true,
			// Only a site the scheduler would send offsite can turn that off
			canSetOffsite: false,
			custom: false,
			hour: '02',
			hourOptions: HOURS,
			// Only plans above the cutoff pick their own backup time
			canSetTime: false,
			// Times we set up for the site ourselves. A site can't give itself more
			// than one backup a day, so it can't edit those times either.
			times: [],
			// Saving before this is true would submit the defaults over whatever
			// the site already has
			loaded: false,
		}
	},
	mounted() {
		this.$site.getBackupSchedule.submit().then((schedule) => {
			this.offsite = schedule.offsite
			this.canSetOffsite = schedule.can_set_offsite
			this.custom = schedule.custom
			this.canSetTime = schedule.can_set_time
			this.times = schedule.times
			if (schedule.times.length) {
				this.hour = timeLocal(schedule.times[0]).slice(0, 2)
			}
			this.loaded = true
		})
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site)
		},
		managed() {
			return this.times.length > 1
		},
		managedTimes() {
			return this.times
				.map((time) => this.labelFor(timeLocal(time).slice(0, 2)))
				.join(', ')
		},
		timezone() {
			return dayjs.tz.guess()
		},
		saving() {
			return this.$site?.updateBackupSchedule?.loading
		},
	},
	methods: {
		labelFor(hour) {
			return HOURS.find((option) => option.value === hour)?.label
		},
		save() {
			// One request for both controls: two would race on the same Site row
			let payload = { offsite: this.offsite }
			// Leave the time out when the dialog shows no time control, so that the
			// site keeps the schedule it has
			if (this.canSetTime && !this.managed) {
				payload.time = this.custom ? timeServer(`${this.hour}:00`) : null
			}
			let promise = this.$site.updateBackupSchedule.submit(payload)
			toast.promise(promise, {
				loading: 'Saving backup schedule...',
				success: () => {
					this.show = false
					return 'Backup schedule saved.'
				},
				error: (e) => getToastErrorMessage(e),
			})
		},
	},
}
</script>
