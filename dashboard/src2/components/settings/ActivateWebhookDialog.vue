<template>
	<Dialog
		:options="{
			title: 'Activate Webhook'
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl label="Endpoint" v-model="webhook.endpoint" disabled />
				<div v-if="request">
					<p class="text-xs text-gray-600">Request</p>
					<pre
						class="mt-2 whitespace-pre-wrap rounded bg-gray-50 px-2 py-1.5 text-sm text-gray-600"
						>{{ request }}</pre
					>
				</div>

				<FormControl
					v-if="response_status_code"
					label="Response Status Code"
					v-model="response_status_code"
					disabled
				/>
				<div v-if="response">
					<p class="text-xs text-gray-600">Response</p>
					<pre
						class="mt-2 max-h-52 overflow-y-auto whitespace-pre-wrap rounded bg-gray-50 px-2 py-1.5 text-sm text-gray-600"
						>{{ response }}</pre
					>
				</div>
				<div class="flex items-center" v-if="validated">
					<ILucideCheck class="h-4 text-green-600" />
					<div class="ml-2 text-sm font-medium text-gray-700">
						Endpoint has been validated
					</div>
				</div>

				<ErrorMessage :message="errorMessage" />
			</div>
		</template>
		<template v-slot:actions>
			<Button
				class="w-full"
				theme="gray"
				variant="solid"
				@click="$resources.validateEndpoint.submit()"
				:loading="$resources.validateEndpoint.loading"
				loadingText="Validating Webhook"
				v-if="!validated"
				>Validate Webhook</Button
			>
			<Button
				class="w-full"
				theme="gray"
				variant="solid"
				@click="$resources.activateWebhook.submit()"
				:loading="$resources.activateWebhook.loading"
				loadingText="Activating Webhook"
				v-if="validated"
				>Activate Webhook</Button
			>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';

export default {
	emits: ['success'],
	props: ['webhook'],
	data() {
		return {
			errorMessage: '',
			validated: false,
			request: null,
			response: null,
			response_status_code: null
		};
	},
	resources: {
		validateEndpoint() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Press Webhook',
						dn: this.webhook.name,
						method: 'validate_endpoint'
					};
				},
				onSuccess: result => {
					const data = result.message;
					this.request = data.request;
					this.response = data.response;
					this.response_status_code = data.response_status_code;
					if (data.success) {
						this.errorMessage = '';
						this.validated = true;
					} else {
						this.validated = false;

						this.errorMessage =
							'Endpoint should return a status between 200 and 300\nPlease check the endpoint and try again';
					}
				},
				onError: e => {
					console.error(e);
					this.errorMessage = e.message;
				}
			};
		},
		activateWebhook() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Press Webhook',
						dn: this.webhook.name,
						method: 'activate'
					};
				},
				onSuccess(e) {
					toast.success('Webhook activated successfully');
					this.$emit('success');
				},
				onError(e) {
					console.error(e);
					this.errorMessage = e.message;
				}
			};
		}
	}
};
</script>
