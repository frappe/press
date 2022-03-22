<template>
	<div>
		<div v-if="!$resources.getSiteAutoUpdateInfo.loading && !autoUpdateEnabled">
			<Alert title="Auto updates are disabled for this site.">
				<template #actions>
					<Button
						type="primary"
						@click="enableAutoUpdate"
						:loading="$resources.enableAutoUpdate.loading"
						loadingText="Enabling"
						>Enable</Button
					>
				</template>
			</Alert>
		</div>
		<div v-else class="md:grid md:grid-cols-2">
			<Card title="Auto Update">
				<template
					#actions
					v-if="!$resources.getSiteAutoUpdateInfo.loading && autoUpdateEnabled"
				>
					<!-- Disable Button -->
					<Button
						@click="disableAutoUpdate"
						:loading="$resources.disableAutoUpdate.loading"
						loadingText="Disabling"
						>Disable Auto Updates</Button
					>
					<Button icon-left="edit" @click="showEditDialog = true">Edit</Button>
				</template>

				<div
					class="divide-y-2"
					v-if="!$resources.getSiteAutoUpdateInfo.loading && autoUpdateEnabled"
				>
					<ListItem
						title="Update cycle"
						:description="
							siteAutoUpdateInfo.update_trigger_frequency || 'Not Set'
						"
					/>

					<!-- For weekly updates only -->
					<ListItem
						v-if="siteAutoUpdateInfo.update_trigger_frequency === 'Weekly'"
						title="On day of the week"
						:description="siteAutoUpdateInfo.update_on_weekday"
					/>

					<ListItem
						title="Update time"
						:description="
							getFormattedTime(siteAutoUpdateInfo.update_trigger_time) ||
							'Not Set'
						"
					/>

					<!-- Day of month description -->
					<div v-if="siteAutoUpdateInfo.update_trigger_frequency === 'Monthly'">
						<ListItem
							v-if="!siteAutoUpdateInfo.update_end_of_month"
							title="On day of the month"
							:description="
								siteAutoUpdateInfo.update_on_day_of_month.toString()
							"
						/>
						<ListItem
							v-else
							title="On day of the month"
							description="End of the month"
						/>
					</div>

					<!-- Last triggered At -->
					<ListItem
						v-if="siteAutoUpdateInfo.auto_update_last_triggered_on"
						title="Last updated on"
						:description="siteAutoUpdateInfo.auto_update_last_triggered_on"
					/>
					<ListItem
						v-else
						title="Last updated on"
						description="Never triggered"
					/>
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
						loadingText="Enabling"
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
					<!-- Edit From -->
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
						:error="$resources.disableAutoUpdate.error"
					/>

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

				<h4 class="mt-2 text-base text-gray-600">
					<strong>Note:</strong> All times are in IST (UTC + 5:30 hours).
				</h4>

				<ErrorMessage class="mt-4" :error="$resources.enableAutoUpdate.error" />
			</Card>
		</div>
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
					name: this.site?.name
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
					name: this.site?.name
				},
				onSuccess() {
					this.$resources.getSiteAutoUpdateInfo.fetch();
				}
			};
		},
		disableAutoUpdate() {
			return {
				method: 'press.api.site.disable_auto_update',
				params: {
					name: this.site?.name
				},
				onSuccess() {
					this.showEditDialog = false;
					this.$resources.getSiteAutoUpdateInfo.fetch();
				}
			};
		},
		updateAutoUpdateInfo() {
			return {
				method: 'press.api.site.update_auto_update_info',
				params: {
					name: this.site?.name,
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
		disableAutoUpdate() {
			this.$resources.disableAutoUpdate.submit();
		},
		getFormattedTime(timeStringFromServer) {
			if (!timeStringFromServer) {
				return;
			}
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
