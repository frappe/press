<template>
	<Dialog
		:options="{
			title: 'Add New Webhook',
			actions: [
				{
					label: 'Add Webhook',
					variant: 'solid',
					onClick: addWebhook,
					loading: $resources?.addWebhook?.loading,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl label="Endpoint" v-model="endpoint" />
				<div>
					<FormControl label="Secret" v-model="secret">
						<template #suffix>
							<FeatherIcon
								class="w-4 cursor-pointer"
								name="refresh-ccw"
								@click="generateRandomSecret"
							/>
						</template>
					</FormControl>
					<p class="mt-2 text-sm text-gray-700">
						<strong>Note:</strong> Secret is optional. Check
						<a
							href="https://docs.frappe.io/cloud/webhook-introduction"
							class="underline"
							target="_blank"
							>the documentation</a
						>
						to learn more
					</p>
				</div>
				<p class="text-base font-medium text-gray-900">
					Select the webhook events
				</p>
				<div
					class="text-center text-sm leading-10 text-gray-500"
					v-if="$resources.events.loading"
				>
					Loading...
				</div>
				<div class="mt-6 flex flex-col gap-4" v-else>
					<Switch
						v-for="event in $resources.events.data"
						:key="event.name"
						:label="event.name"
						:description="event.description"
						:modelValue="isEventSelected(event.name)"
						@update:modelValue="selectEvent(event.name)"
						size="sm"
					/>
				</div>
				<ErrorMessage :message="errorMessage || $resources.addWebhook.error" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Switch } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	emits: ['success'],
	data() {
		return {
			endpoint: '',
			secret: '',
			selectedEvents: [],
			errorMessage: '',
		};
	},
	components: { Switch },
	mounted() {
		if (this.selectedEvents.length) {
			this.selectedEvents = this.selectedEvents.map((event) => event.name);
		}
	},
	resources: {
		events() {
			return {
				url: 'press.api.webhook.available_events',
				inititalData: [],
				auto: true,
			};
		},
		addWebhook() {
			return {
				url: 'press.api.webhook.add',
				params: {
					endpoint: this.endpoint,
					secret: this.secret,
					events: this.selectedEvents,
				},
				onSuccess() {
					toast.success('Webhook added successfully');
					this.$emit('success');
				},
			};
		},
	},
	computed: {},
	methods: {
		generateRandomSecret() {
			this.secret = Array(30)
				.fill(0)
				.map(
					() =>
						'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[
							Math.floor(Math.random() * 62)
						],
				)
				.join('');
		},
		selectEvent(event) {
			if (this.selectedEvents.includes(event)) {
				this.selectedEvents = this.selectedEvents.filter((e) => e !== event);
			} else {
				this.selectedEvents.push(event);
			}
		},
		isEventSelected(event) {
			return this.selectedEvents.includes(event);
		},
		addWebhook() {
			if (!this.endpoint) {
				this.errorMessage = 'Provide a valid webhook endpoint';
				return;
			}
			if (!this.selectedEvents.length) {
				this.errorMessage = 'Please enable at least one event';
				return;
			}
			this.errorMessage = '';
			this.$resources.addWebhook.submit();
		},
	},
};
</script>
