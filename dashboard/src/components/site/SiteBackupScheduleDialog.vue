<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Backup Schedule',
			actions: managed
				? []
				: [
						{
							label: 'Save',
							variant: 'solid',
							disabled: !loaded,
							loading: $site?.updateBackupSchedule?.loading,
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

			<p v-else-if="managed" class="text-base leading-5 text-ink-gray-7">
				Your site backs up at {{ managedTimes }} every day. We set that up for
				you — write to support to change it.
			</p>

			<div v-else class="flex flex-col gap-5">
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
						<span class="text-base font-medium leading-normal text-ink-gray-8">
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
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource, Switch } from 'frappe-ui';
import { toast } from 'vue-sonner';
import dayjs, { timeLocal, timeServer } from '../../utils/dayjs';
import { getToastErrorMessage } from '../../utils/toast';

// Backups fire on the hour, so offering minutes would promise precision the
// scheduler doesn't have.
const HOURS = Array.from({ length: 24 }, (_, hour) => ({
	label: dayjs().hour(hour).minute(0).format('h:mm A'),
	value: String(hour).padStart(2, '0'),
}));

export default {
	props: ['site'],
	components: { Switch },
	data() {
		return {
			show: true,
			custom: false,
			hour: '02',
			hourOptions: HOURS,
			// Times we set up for the site ourselves. A site can't give itself more
			// than one backup a day, so it can't edit those times either.
			times: [],
			// Saving before this is true would submit the defaults over whatever
			// the site already has
			loaded: false,
		};
	},
	mounted() {
		this.$site.getBackupSchedule.submit().then((schedule) => {
			this.custom = schedule.custom;
			this.times = schedule.times;
			if (schedule.times.length) {
				this.hour = timeLocal(schedule.times[0]).slice(0, 2);
			}
			this.loaded = true;
		});
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		managed() {
			return this.times.length > 1;
		},
		managedTimes() {
			return this.times
				.map((time) => this.labelFor(timeLocal(time).slice(0, 2)))
				.join(', ');
		},
		timezone() {
			return dayjs.tz.guess();
		},
	},
	methods: {
		labelFor(hour) {
			return HOURS.find((option) => option.value === hour)?.label;
		},
		save() {
			let promise = this.$site.updateBackupSchedule.submit({
				time: this.custom ? timeServer(`${this.hour}:00`) : null,
			});
			toast.promise(promise, {
				loading: 'Saving backup schedule...',
				success: () => {
					this.show = false;
					return 'Backup schedule saved.';
				},
				error: (e) => getToastErrorMessage(e),
			});
		},
	},
};
</script>
