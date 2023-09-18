<template>
	<div>
		<label class="text-lg font-semibold"> Choose a hostname </label>
		<p class="text-base text-gray-700">
			Give your site a unique name. It can only contain alphanumeric characters
			and dashes.
		</p>
		<div class="mt-4 flex">
			<input
				class="form-input z-10 w-full rounded-r-none"
				type="text"
				:value="modelValue"
				placeholder="subdomain"
				@change="subdomainChange"
			/>
			<div class="flex items-center rounded-r bg-gray-100 px-4 text-base">
				.{{ domain }}
			</div>
		</div>
		<div class="mt-1">
			<div
				v-if="subdomainAvailable"
				class="text-sm text-green-600"
				role="alert"
			>
				{{ modelValue }}.{{ domain }} is available
			</div>
			<ErrorMessage :message="errorMessage" />
		</div>
	</div>
</template>
<script>
import { validateSubdomain } from '@/utils';

export default {
	name: 'Hostname',
	props: ['modelValue'],
	emits: ['update:modelValue', 'error'],
	data() {
		return {
			subdomainAvailable: false,
			errorMessage: null
		};
	},
	resources: {
		domain() {
			return {
				url: 'press.api.site.get_domain',
				auto: true
			};
		}
	},
	computed: {
		domain() {
			return this.$resources.domain.data;
		}
	},
	methods: {
		async subdomainChange(e) {
			let subdomain = e.target.value;
			this.$emit('update:modelValue', subdomain);
			this.subdomainAvailable = false;

			let error = this.validateSubdomain(subdomain);
			if (!error) {
				let subdomainTaken = await this.$call('press.api.site.exists', {
					subdomain,
					domain: this.domain
				});
				if (subdomainTaken) {
					error = `${subdomain}.${this.domain} already exists.`;
				} else {
					this.subdomainAvailable = true;
				}
			}
			this.errorMessage = error;
			this.$emit('error', error);
		},
		validateSubdomain(subdomain) {
			return validateSubdomain(subdomain);
		}
	}
};
</script>
