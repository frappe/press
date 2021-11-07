<template>
	<div class="md:grid md:grid-cols-2">
		<Card title="Schedule Site Auto Updates">
			<template #actions>
				<Button icon-left="edit" @click="showEditDialog = true">Edit</Button>
			</template>

			<div
				class="divide-y-2"
				v-if="!$resources.getSiteAutoUpdateInfo.loading && autoUpdateEnabled"
			>
				<ListItem
					title="Trigger Frequency"
					:description="siteAutoUpdateInfo.update_trigger_frequency"
				/>

				<!-- For weekly updates only -->
				<ListItem
					v-if="siteAutoUpdateInfo.update_trigger_frequency === 'Weekly'"
					title="Trigger on Weekday"
					:description="siteAutoUpdateInfo.update_on_weekday"
				/>

				<ListItem
					title="Trigger Time"
					:description="
						getFormattedTime(siteAutoUpdateInfo.update_trigger_time)
					"
				/>

				<!-- Last triggered At -->
				<ListItem
					v-if="siteAutoUpdateInfo.auto_update_last_triggered_on"
					title="Last Triggered At"
					:description="siteAutoUpdateInfo.auto_update_last_triggered_on"
				/>
				<ListItem
					v-else
					title="Last Triggered At"
					description="Never triggered"
				/>

				<!-- Day of month description -->
				<div v-if="siteAutoUpdateInfo.update_trigger_frequency === 'Monthly'">
					<ListItem
						v-if="!siteAutoUpdateInfo.update_end_of_month"
						title="Trigger on Month day"
						:description="siteAutoUpdateInfo.update_on_day_of_month.toString()"
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

			<Dialog title="Schedule Auto Updates" v-model="showEditDialog">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<Input
						type="select"
						label="Update Frequency"
						:options="frequencyOptions"
						v-model="updateFrequency"
					/>

					<Input
						type="select"
						:options="timeOptions"
						label="Update time"
						v-model="updateTime"
					/>

					<Input
						v-if="updateFrequency === 'Weekly'"
						type="select"
						label="Day of the week"
						:options="weekDayOptions"
						v-model="weekDay"
					/>

					<Input
						v-if="updateFrequency === 'Monthly'"
						type="select"
						:options="monthDayOptions"
						label="Day of the month"
						v-model.number="monthDay"
					/>
					<Input
						v-if="updateFrequency === 'Monthly'"
						type="checkbox"
						label="Update end of month"
						:checked="endOfMonth"
						v-model="endOfMonth"
					/>
				</div>
				<ErrorMessage
					class="mt-4"
					:error="$resources.updateAutoUpdateInfo.error"
				/>
				<template #actions>
					<Button
						type="primary"
						:loading="$resources.updateAutoUpdateInfo.loading"
						loadingText="Saving..."
						@click="$resources.updateAutoUpdateInfo.submit()"
					>
						Save changes
					</Button>
				</template>
			</Dialog>
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
			updateTime: '',
			showEditDialog: false
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
					this.updateTime = this.getFormattedTime(data.update_trigger_time);
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
		},
		updateAutoUpdateInfo() {
			return {
				method: 'press.api.site.update_auto_update_info',
				params: {
					name: this.site.name,
					info: {
						auto_updates_scheduled: this.autoUpdateEnabled,
						update_trigger_frequency: this.updateFrequency,
						update_on_weekday: this.weekDay,
						update_end_of_month: this.endOfMonth,
						update_on_day_of_month: this.monthDay,
						auto_update_last_triggered_on: this.lastTriggeredAt,
						update_trigger_time: this.updateTime
					}
				},
				onSuccess() {
					this.showEditDialog = false;
					this.$resources.getSiteAutoUpdateInfo.fetch();
				}
			};
		}
	},
	methods: {
		enableAutoUpdate() {
			this.$resources.enableAutoUpdate.submit();
		},
		getFormattedTime(timeStringFromServer) {
			// E.g. "8:19:00" --> "08:19"
			let timeParts = timeStringFromServer.split(':').slice(0, 2);
			return timeParts[0].padStart(2, '0') + ':' + timeParts[1];
		}
	},
	computed: {
		siteAutoUpdateInfo() {
			if (
				!this.$resources.getSiteAutoUpdateInfo.loading &&
				this.$resources.getSiteAutoUpdateInfo.data
			) {
				return this.$resources.getSiteAutoUpdateInfo.data;
			}
		},
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
