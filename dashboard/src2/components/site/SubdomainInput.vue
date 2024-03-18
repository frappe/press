<template>
	<div class="md:w-1/2">
		<div class="mt-2 items-center">
			<div class="col-span-2 flex w-full">
				<TextInput
					class="flex-1 rounded-r-none"
					placeholder="Subdomain"
					v-model="subdomain"
				/>
				<div class="flex items-center rounded-r bg-gray-100 px-4 text-base">
					.{{ domain }}
				</div>
			</div>
		</div>
		<div class="mt-1">
			<ErrorMessage :message="error" />
			<template v-if="!error">
				<div v-if="!subdomainExists" class="text-sm text-green-600">
					{{ subdomain }}.{{ domain }} is available
				</div>
				<div v-else class="text-sm text-red-600">
					{{ subdomain }}.{{ domain }} is not available
				</div>
			</template>
		</div>
	</div>
</template>

<script>
import { validateSubdomain } from '../../../src/utils';

export default {
	props: ['domain', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			error: '',
			subdomain: this.modelValue || '',
			subdomainExists: false
		};
	},
	watch: {
		subdomain: {
			handler() {
				this.$resources.subdomainExists.submit();
			}
		}
	},
	resources: {
		subdomainExists() {
			return {
				url: 'press.api.site.exists',
				debounce: 500,
				params: {
					domain: this.domain,
					subdomain: this.subdomain
				},
				validate() {
					return validateSubdomain(this.subdomain);
				},
				onSuccess(data) {
					this.subdomainExists = data;
					this.error = '';
					this.$emit('update:modelValue', this.subdomain);
				},
				onError(err) {
					this.error = err;
				}
			};
		}
	}
};
</script>
