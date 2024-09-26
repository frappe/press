<template>
	<div v-if="$resources.attempt.loading">Loading...</div>
	<div v-else class="space-y-4">
		<div>
			<p class="text-xs text-gray-600">Endpoint</p>
			<p class="mt-2 text-sm text-gray-700">
				{{ $resources.attempt?.data?.endpoint }}
			</p>
		</div>
		<div>
			<p class="text-xs text-gray-600">Request</p>
			<pre
				class="mt-2 max-h-52 overflow-y-auto whitespace-pre-wrap rounded bg-gray-50 px-2 py-1.5 text-sm text-gray-600"
				>{{ $resources.attempt?.data?.request_payload }}</pre
			>
		</div>
		<div
			v-if="
				is_valid_status_code($resources.attempt?.data?.response_status_code)
			"
		>
			<p class="text-xs text-gray-600">Response Status Code</p>
			<p class="mt-2 text-sm text-gray-700">
				{{ $resources.attempt?.data?.response_status_code }}
			</p>
		</div>
		<div v-if="$resources.attempt?.data?.response_body">
			<p class="text-xs text-gray-600">Response</p>
			<pre
				class="mt-2 max-h-52 overflow-y-auto whitespace-pre-wrap rounded bg-gray-50 px-2 py-1.5 text-sm text-gray-600"
				>{{ $resources.attempt?.data?.response_body }}</pre
			>
		</div>
		<div>
			<p class="text-xs text-gray-600">Timestamp</p>
			<p class="mt-2 text-sm text-gray-700">
				{{ $resources.attempt?.data?.creation }}
			</p>
		</div>
	</div>
	<ErrorMessage class="mt-4" :message="$resources.attempt.error" />
</template>

<script>
import { toast } from 'vue-sonner';

export default {
	props: ['id'],
	data() {
		return {
			endpoint: null,
			errorMessage: '',
			validated: false,
			request: null,
			response: null,
			response_status_code: null
		};
	},
	resources: {
		attempt() {
			return {
				url: 'press.api.webhook.attempt',
				makeParams: () => {
					return {
						name: this.$props.id
					};
				},
				auto: true
			};
		}
	},
	computed: {
		data() {
			return this.$resources.attempt.data || {};
		}
	},
	methods: {
		is_valid_status_code(status_code) {
			if (!status_code) return false;
			if (status_code == '0') return false;
			return true;
		}
	}
};
</script>
