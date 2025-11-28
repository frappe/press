<template>
	<Dialog
		v-model="show"
		:options="{ title: `Schedule Autoscale`, size: '2xl' }"
	>
		<template #body-content>
			<div class="flex flex-col space-y-6">
				<div class="leading-relaxed">
					<p class="font-medium mb-1">Autoscale Scheduling Rules</p>

					<ul class="list-disc list-inside space-y-1">
						<li>
							Scale up and scale down times must be at least
							<strong>30 minutes apart</strong>.
						</li>
						<li>The selected times must be in the future.</li>
						<li>
							A new scale up can only occur after the server has been scaled
							down for at least <strong>5 minutes</strong>.
						</li>
					</ul>
				</div>
				<div
					class="bg-gray-50 border border-gray-200 rounded-lg p-4 mt-4 space-y-6"
				>
					<div class="flex flex-col space-y-2">
						<label class="font-medium text-gray-700">Scale Up Start Time</label>
						<DateTimePicker
							v-model="scaleUpdateTime"
							variant="subtle"
							placeholder="Select date & time"
						/>
					</div>

					<!-- Scale Down -->
					<div class="flex flex-col space-y-2">
						<label class="font-medium text-gray-700"
							>Scale Down Start Time</label
						>
						<DateTimePicker
							v-model="scaleDowndateTime"
							variant="subtle"
							placeholder="Select date & time"
						/>
					</div>
				</div>
				<Button
					variant="solid"
					theme="gray"
					@click="scheduleAutoscale"
					class="w-full rounded-lg mt-4 py-3"
				>
					Schedule Autoscale
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Dialog, DateTimePicker } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	name: 'AutoscaleScheduleDialog',

	components: {
		Dialog,
		DateTimePicker,
	},

	props: {
		server: {
			type: String,
			required: true,
		},
	},

	data() {
		return {
			show: true,
			scaleUpdateTime: null,
			scaleDowndateTime: null,
		};
	},

	resources: {
		scheduleAutoscale() {
			return {
				url: 'press.api.server.schedule_auto_scale',
				makeParams: () => {
					return {
						name: this.server,
						scheduled_scale_up_time: this.scaleUpdateTime,
						scheduled_scale_down_time: this.scaleDowndateTime,
					};
				},
				auto: false,
			};
		},
	},

	methods: {
		scheduleAutoscale() {
			if (!this.scaleUpdateTime || !this.scaleDowndateTime) {
				return toast.error('Both times are required.');
			}

			const now = new Date();
			const up = new Date(this.scaleUpdateTime);
			const down = new Date(this.scaleDowndateTime);

			// Future validation
			if (up <= now) {
				return toast.error('Scale up time must be in the future.');
			}
			if (down <= now) {
				return toast.error('Scale down time must be in the future.');
			}

			// Need a 30 minutes
			const diffMinutes = (down - up) / (1000 * 60);
			if (diffMinutes < 30) {
				return toast.error(
					'Scale down time must be at least 30 minutes after scale up.',
				);
			}

			toast.promise(this.$resources.scheduleAutoscale.submit(), {
				loading: 'Scheduling autoscale...',
				success: () => {
					this.show = false;
					return 'Scheduled autoscale';
				},
				error: (err) => {
					console.log(err);
					return 'Failed scheduled autoscale';
				},
			});
		},
	},
};
</script>
