<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Backup Schedule',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					loading: $site?.updateBackupSchedule?.loading,
					onClick: save,
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<Switch
					v-model="custom"
					label="Pick backup times"
					description="Move backups off your working hours instead of leaving them to the default schedule"
				/>

				<p v-if="!custom" class="text-base text-ink-gray-6">
					Backups are taken automatically every 6 hours.
				</p>

				<div v-else class="flex flex-col gap-3">
					<div
						v-for="(time, index) in times"
						:key="index"
						class="flex items-center gap-2"
					>
						<FormControl
							class="w-full"
							type="time"
							v-model="times[index]"
						/>
						<Button
							v-if="times.length > 1"
							icon="x"
							@click="times.splice(index, 1)"
						/>
					</div>

					<Button
						v-if="times.length < maximumTimes"
						class="w-fit"
						icon-left="plus"
						@click="addTime"
					>
						Add time
					</Button>

					<p class="text-p-sm text-ink-gray-5">
						Times are in your timezone ({{ timezone }}). A backup starts
						within the hour you pick, and replaces the default 6 hourly
						schedule.
					</p>
				</div>

				<ErrorMessage :message="errorMessage" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Switch, getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import dayjs, { timeLocal, timeServer } from '../../utils/dayjs';
import { getToastErrorMessage } from '../../utils/toast';

export default {
	props: ['site'],
	components: { Switch },
	data() {
		return {
			show: true,
			custom: false,
			times: ['02:00'],
			maximumTimes: 4,
			errorMessage: null,
		};
	},
	mounted() {
		this.$site.getBackupSchedule.submit().then((schedule) => {
			this.custom = schedule.custom;
			if (schedule.times.length) {
				this.times = schedule.times.map(timeLocal);
			}
		});
	},
	computed: {
		$site() {
			return getCachedDocumentResource('Site', this.site);
		},
		timezone() {
			return dayjs.tz.guess();
		},
	},
	methods: {
		addTime() {
			// An hour after the last one, so a fresh row doesn't land in a taken hour
			let last = this.times[this.times.length - 1] || '01:00';
			this.times.push(dayjs(`2000-01-01 ${last}`).add(1, 'hour').format('HH:mm'));
		},
		save() {
			this.errorMessage = this.validate();
			if (this.errorMessage) return;

			let promise = this.$site.updateBackupSchedule.submit({
				times: this.custom ? this.times.map(timeServer) : [],
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
		validate() {
			if (!this.custom) return null;
			if (this.times.some((time) => !time))
				return 'Pick a time for every backup.';
			// The scheduler runs once an hour, so two backups in the same hour
			// would silently collapse into one.
			let hours = this.times.map((time) => timeServer(time).split(':')[0]);
			if (new Set(hours).size !== hours.length)
				return 'Backups have to be at least an hour apart.';
			return null;
		},
	},
};
</script>
