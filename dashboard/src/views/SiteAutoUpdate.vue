<template>
	<div class="md:grid md:grid-cols-2">
		<Card title="Schedule Site Auto Updates">
			<template #actions>
				<Button icon-left="edit">Edit</Button>
			</template>
			<!-- <div class="space-y-4">
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
			</div> -->

			<div
				class="divide-y-2"
				v-if="!$resources.getSiteAutoUpdateInfo.loading && autoUpdateEnabled"
			>
				<ListItem title="Trigger Frequency" :description="updateFrequency" />

				<!-- For weekly updates only -->
				<ListItem
					v-if="updateFrequency === 'Weekly'"
					title="Trigger on Weekday"
					:description="weekDay"
				/>

				<ListItem title="Trigger Time" :description="updateTime" />

				<!-- Last triggered At -->
				<ListItem
					v-if="lastTriggeredAt"
					title="Last Triggered At"
					:description="lastTriggeredAt"
				/>
				<ListItem
					v-else
					title="Last Triggered At"
					description="Never triggered"
				/>

				<!-- Day of month description -->
				<div v-if="updateFrequency === 'Monthly'">
					<ListItem
						v-if="!endOfMonth"
						title="Trigger on Month day"
						:description="monthDay.toString()"
					/>
					<ListItem
						v-else
						title="Trigger on Month day"
						description="End of month"
					/>
				</div>
			</div>

			<!-- If updates are not enabled, show button -->
			<div
				class="py-10 text-center"
				v-if="!$resources.getSiteAutoUpdateInfo.loading && !autoUpdateEnabled"
			>
				<h3 class="text-sm text-gray-800">
					Auto updates are disabled for this site.
				</h3>
				<Button
					class="mt-3"
					type="primary"
					@click="enableAutoUpdate"
					:loading="this.$resources.enableAutoUpdate.loading"
					>Enable Auto Updates</Button
				>
			</div>

			<!-- Loading Spinner button -->
			<div
				v-if="$resources.getSiteAutoUpdateInfo.loading"
				class="py-10 text-center"
			>
				<Button :loading="true">Loading</Button>
			</div>
		</Card>
	</div>
</template>

<script>
export default {
	name: 'SiteAutoUpdate',
	props: ['site'],
	data() {
		return {
			autoUpdateEnabled: null,
			lastTriggeredAt: null,
			updateFrequency: '',
			weekDay: '',
			monthDay: '',
			endOfMonth: false,
			updateTime: ''
		};
	},
	resources: {
		getSiteAutoUpdateInfo() {
			return {
				method: 'press.api.site.get_auto_update_info',
				params: {
					name: this.site.name
				},
				auto: true,
				onSuccess(data) {
					this.autoUpdateEnabled = data.auto_updates_scheduled;
					this.updateFrequency = data.update_trigger_frequency;
					this.weekDay = data.update_on_weekday;
					this.endOfMonth = data.update_end_of_month;
					this.monthDay = data.update_on_day_of_month;
					this.lastTriggeredAt = data.auto_update_last_triggered_on;
					this.updateTime = data.update_trigger_time;
				}
			};
		},
		enableAutoUpdate() {
			return {
				method: 'press.api.site.enable_auto_update',
				params: {
					name: this.site.name
				},
				onSuccess() {
					this.$resources.getSiteAutoUpdateInfo.fetch();
				}
			};
		}
	},
	methods: {
		enableAutoUpdate() {
			this.$resources.enableAutoUpdate.submit();
		}
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
