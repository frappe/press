<template>
	<div class="md:grid md:grid-cols-2">
		<Card title="Schedule Site Auto Updates">
			<template #actions>
				<Button icon-left="edit">Edit</Button>
			</template>
			<div class="space-y-4">
				<Input
					type="checkbox"
					label="Enable Site Auto Update"
					v-model="autoUpdateEnabled"
				/>
				<Input
					type="select"
					label="Update Frequency"
					:options="frequencyOptions"
					v-model="updateFrequency"
				/>
				<div>
					<Input
						type="select"
						label="Day of the week"
						:options="weekDayOptions"
						v-model="weekDay"
					/>
				</div>
				<Input
					type="select"
					:options="monthDayOptions"
					label="Day of the month"
					v-model="monthDay"
				/>
				<Input
					type="checkbox"
					label="Update end of month"
					v-model="endOfMonth"
				/>
				<Input
					type="select"
					:options="timeOptions"
					label="Update time"
					v-model="updateTime"
				/>
			</div>
		</Card>
	</div>
</template>

<script>
export default {
	name: 'SiteAutoUpdate',
	props: ['site'],
	data: {
		autoUpdateEnabled: false,
		updateFrequency: '',
		weekDay: 'Sunday',
		monthDay: '',
		endOfMonth: false,
		updateTime: ''
	},
	resources: {
		getSiteAutoUpdateInfo() {
			return {
				method: 'press.api.site.set_auto_update_info'
			};
		}
	},
    mounted() {
        this.autoUpdateEnabled = this.site.auto_updates_scheduled;
    },
	computed: {
		frequencyOptions() {
			return ['Daily', 'Weekly', 'Monthly'];
		},
		weekDayOptions() {
			return [
				'Sunday',
				'Monday',
				'Tuesday',
				'Wednesday',
				'Thursday',
				'Friday',
				'Saturday'
			];
		},
		monthDayOptions() {
			let ops = [];
			for (let i = 1; i < 31; ++i) {
				ops.push(i.toString());
			}
			return ops;
		},
		timeOptions() {
			let ops = [];
			for (let i = 0; i < 24; i++) {
				const currentHour = String(i).padStart(2, '0');
				ops.push(`${currentHour}:00`);
				ops.push(`${currentHour}:30`);
			}
			return ops;
		}
	}
};
</script>
