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
				<div class="rounded-md bg-surface-gray-1 p-3">
					<Switch
						v-model="custom"
						label="Choose when backups run"
						:description="
							custom
								? 'Backups run only at the times below'
								: 'Backups run every 6 hours, whenever that falls'
						"
					/>
				</div>

				<div v-if="custom" class="flex flex-col gap-3">
					<div class="flex items-baseline justify-between">
						<span class="text-base font-medium text-ink-gray-8">
							Backup times
						</span>
						<span class="text-p-sm text-ink-gray-5">
							{{ times.length }} of {{ maximumTimes }}
						</span>
					</div>

					<div class="grid grid-cols-2 gap-x-3 gap-y-2">
						<div
							v-for="(time, index) in times"
							:key="index"
							class="flex items-center gap-1"
						>
							<FormControl
								class="flex-1"
								type="time"
								v-model="times[index]"
							/>
							<Button
								v-if="times.length > 1"
								variant="ghost"
								icon="x"
								:label="`Remove ${time}`"
								@click="times.splice(index, 1)"
							/>
						</div>
					</div>

					<Button
						v-if="times.length < maximumTimes"
						class="w-fit"
						variant="subtle"
						icon-left="plus"
						@click="addTime"
					>
						Add time
					</Button>

					<p class="text-p-sm leading-5 text-ink-gray-5">
						Times are in your timezone ({{ timezone }}). A backup starts
						within the hour you pick.
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
