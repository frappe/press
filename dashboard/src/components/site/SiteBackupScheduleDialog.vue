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
			<div class="flex flex-col gap-5">
				<Switch
					v-model="custom"
					label="Choose when backups run"
					:description="
						custom
							? 'Backups run only at the hours below'
							: 'Backups run every 6 hours, whenever that falls'
					"
				/>

				<div v-if="custom" class="flex flex-col gap-3">
					<div class="flex items-baseline justify-between">
						<span class="text-base font-medium text-ink-gray-8">
							Backup times
						</span>
						<span class="text-p-sm text-ink-gray-5">
							{{ hours.length }} of {{ maximumTimes }}
						</span>
					</div>

					<div class="flex flex-col gap-2">
						<div
							v-for="(hour, index) in hours"
							:key="index"
							class="flex items-center gap-2"
						>
							<FormControl
								class="w-36"
								type="select"
								variant="outline"
								:options="optionsFor(index)"
								v-model="hours[index]"
							/>
							<Button
								v-if="hours.length > 1"
								variant="ghost"
								icon="x"
								:label="`Remove ${labelFor(hour)}`"
								@click="hours.splice(index, 1)"
							/>
						</div>
					</div>

					<Button
						v-if="hours.length < maximumTimes"
						class="w-fit"
						variant="subtle"
						icon-left="plus"
						@click="addHour"
					>
						Add time
					</Button>

					<p class="text-p-sm leading-5 text-ink-gray-5">
						A backup starts within the hour you pick. Times are in your
						timezone ({{ timezone }}).
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Switch, getCachedDocumentResource } from 'frappe-ui';
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
			hours: ['02'],
			maximumTimes: 4,
		};
	},
	mounted() {
		this.$site.getBackupSchedule.submit().then((schedule) => {
			this.custom = schedule.custom;
			if (schedule.times.length) {
				this.hours = schedule.times.map((time) => timeLocal(time).slice(0, 2));
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
		// Hiding the hours already taken is what keeps two backups out of the same
		// hour, where the scheduler would run only one of them
		optionsFor(index) {
			let taken = this.hours.filter((_, i) => i !== index);
			return HOURS.filter((option) => !taken.includes(option.value));
		},
		labelFor(hour) {
			return HOURS.find((option) => option.value === hour)?.label;
		},
		// Carry on from the last hour picked rather than filling up from midnight
		addHour() {
			let start = Number(this.hours[this.hours.length - 1] ?? -1) + 1;
			let order = HOURS.slice(start).concat(HOURS.slice(0, start));
			this.hours.push(order.find((option) => !this.hours.includes(option.value)).value);
		},
		save() {
			let promise = this.$site.updateBackupSchedule.submit({
				times: this.custom
					? this.hours.map((hour) => timeServer(`${hour}:00`))
					: [],
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
