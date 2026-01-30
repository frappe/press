<template>
	<Dialog
		:options="{
			title: 'Edit Webhook',
			actions: [
				{
					label: 'Save Changes',
					variant: 'solid',
					onClick: updateWebhook,
					loading: this.$resources.updateWebhook.loading,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<div>
					<FormControl label="Endpoint" v-model="endpoint" />
					<p class="mt-1.5 text-sm text-gray-700">
						If you change the endpoint, make sure to activate the webhook again.
					</p>
				</div>
				<div v-if="!updateSecret">
					<p class="block text-xs text-gray-600">Secret</p>
					<div
						class="mt-1 flex items-center justify-between text-base text-gray-700"
					>
						<p>Want to change the secret?</p>
						<Button @click="updateSecret = true">Edit Secret</Button>
					</div>
				</div>
				<div v-else>
					<FormControl label="Secret" v-model="secret">
						<template #suffix>
							<FeatherIcon
								class="w-4 cursor-pointer"
								name="refresh-ccw"
								@click="generateRandomSecret"
							/>
						</template>
					</FormControl>
					<p class="mt-1.5 text-sm text-gray-700">
						<secret>Note:</secret> Secret is optional. Check
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
				<div class="mt-6 flex flex-col gap-3" v-else>
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
				<ErrorMessage
					:message="errorMessage || $resources.updateWebhook.error"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Switch } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { getToastErrorMessage } from '../../utils/toast';

export default {
	emits: ['success'],
	props: ['webhook'],
	data() {
		return {
			endpoint: '',
			secret: '',
			updateSecret: false,
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
		fetchWebhookInfo() {
			return {
				url: 'press.api.client.get',
				params: {
					doctype: 'Press Webhook',
					name: this.webhook.name,
				},
				auto: true,
				onSuccess: (doc) => {
					this.endpoint = doc.endpoint;
					this.selectedEvents = doc.events.map((event) => event.event);
				},
			};
		},
		updateWebhook() {
			return {
				url: 'press.api.webhook.update',
				validate: () => {
					if (!this.selectedEvents) {
						return 'Please enable at least one event';
					}
				},
				makeParams: () => {
					return {
						name: this.webhook.name,
						endpoint: this.endpoint,
						secret: this.updateSecret ? this.secret : '',
						events: this.selectedEvents,
					};
				},
				onSuccess: () => {
					toast.success('Webhook updated successfully');
					const activationRequired = this.webhook.endpoint !== this.endpoint;
					this.$emit('success', activationRequired);
				},
				onError: (e) => {
					toast.error(
						getToastErrorMessage(
							e,
							'Failed to update webhook. Please try again',
						),
					);
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
		updateWebhook() {
			if (this.selectedEvents.length === 0) {
				this.errorMessage = 'Please select at least one event to add';
				return;
			}
			this.errorMessage = '';
			this.$resources.updateWebhook.submit();
		},
	},
};
</script>
