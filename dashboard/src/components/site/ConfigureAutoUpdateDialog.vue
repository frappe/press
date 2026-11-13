<template>
	<Dialog v-model="show" :options="{ title: 'Configure Auto Update' }">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<Switch
					v-model="enableAutoUpdate"
					label="Enable Auto Update"
					description="Automatically schedule site updates whenever available"
				/>

				<!-- A site that already has auto update on never sees the toast,
				     and the window is nowhere else in the dashboard. -->
				<div
					v-if="enableAutoUpdate && showUpdateWindow"
					class="flex flex-col gap-1"
				>
					<span class="text-base font-medium leading-normal text-ink-gray-8">
						Update window
					</span>
					<LoadingIndicator
						v-if="$site.getAutoUpdateWindow.loading"
						class="h-4 w-4 text-ink-gray-5"
					/>
					<ErrorMessage
						v-else-if="$site.getAutoUpdateWindow.error"
						:message="$site.getAutoUpdateWindow.error"
					/>
					<span v-else class="text-p-sm text-ink-gray-7">
						{{ windowDescription }}
					</span>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource, Switch } from 'frappe-ui'
import { toast } from 'vue-sonner'
import dayjs from '../../utils/dayjs'

export default {
	props: {
		site: {
			type: String,
			required: true,
		},
	},
	components: { Switch },
	data() {
		return {
			show: true,
			updateWindow: null,
		}
	},
	mounted() {
		this.$site.getAutoUpdateWindow.submit().then((updateWindow) => {
			this.updateWindow = updateWindow
		})
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site)
		},
		enableAutoUpdate: {
			get() {
				return !this.$site?.doc.skip_auto_updates
			},
			set(value) {
				const saved = this.$site.setValue.submit({ skip_auto_updates: !value })
				if (!value) return
				// The same sentence as the dialog, so the user reads one wording.
				saved.then(() => {
					if (this.windowDescription) {
						toast.success('Auto update is on', {
							description: this.windowDescription,
						})
					}
				})
			},
		},
		showUpdateWindow() {
			const resource = this.$site.getAutoUpdateWindow
			return Boolean(
				resource.loading || resource.error || this.windowDescription,
			)
		},
		windowDescription() {
			if (!this.updateWindow) return null

			const timezone = this.updateWindow.timezone
			// A site with its own schedule runs on the clock of the platform. Every
			// other site updates in the off hours of its own timezone.
			if (!this.updateWindow.windows) {
				const time = this.formatTime(this.updateWindow.time)
				return `${this.frequencyText()} at ${time} (${timezone})`
			}

			const hours = this.hoursText(this.updateWindow.windows)
			if (!hours) return null
			return `${hours}, site time (${timezone})`
		},
	},
	methods: {
		formatHour(hour) {
			// The hours are whole hours, so the minutes would only be noise.
			// The last window ends at hour 24, which is midnight.
			return dayjs()
				.hour(hour % 24)
				.format('h A')
		},
		formatTime(time) {
			if (!time) return ''
			return dayjs(`2000-01-01 ${time}`).format('h:mm A')
		},
		hoursText(windows) {
			return windows
				.map(
					([start, end]) =>
						`${this.formatHour(start)} – ${this.formatHour(end)}`,
				)
				.join(', ')
		},
		frequencyText() {
			const { frequency, weekday, day_of_month, end_of_month } =
				this.updateWindow
			if (frequency === 'Weekly') return `Every ${weekday}`
			if (frequency === 'Monthly') {
				return end_of_month
					? 'On the last day of every month'
					: `On day ${day_of_month} of every month`
			}
			return 'Every day'
		},
	},
}
</script>
