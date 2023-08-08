<template>
	<div class="min-h-screen bg-gray-50" v-if="saasProduct.data">
		<LoginBox :title="state == 'Pending' ? 'Create your site' : ''">
			<template #logo>
				<div class="mx-auto flex flex-col items-center">
					<img
						class="mb-1"
						v-if="saasProduct.data.logo"
						:src="saasProduct.data.logo"
						:alt="saasProduct.data.title"
					/>
					<div class="text-4xl font-semibold text-gray-900" v-else>
						{{ saasProduct.data.title }}
					</div>
					<div class="text-base text-gray-700">Powered by Frappe Cloud</div>
				</div>
			</template>
			<div class="space-y-3" v-if="state == 'Pending'">
				<FormControl
					label="Your Email"
					:modelValue="$account.user.email"
					:disabled="true"
				/>
				<FormControl
					class="subdomain mt-2"
					label="Site Name"
					v-model="subdomain"
					@keydown.enter="createSite.submit()"
				>
					<template #suffix>
						<div
							ref="domainSuffix"
							class="flex items-center text-base text-gray-600"
						>
							.{{ saasProduct.data.domain || 'frappe.cloud' }}
						</div>
					</template>
				</FormControl>
				<ErrorMessage :message="createSite.error" />
				<Button
					class="w-full"
					variant="solid"
					@click="createSite.submit()"
					:loading="createSite.loading"
				>
					Create
				</Button>
			</div>
			<div v-else-if="state == 'Wait for Site'">
				<Progress
					label="Creating site"
					:value="siteProgress.data?.progress || 0"
					size="md"
				/>
				<ErrorMessage
					:message="siteProgress.data?.error ? 'An error occurred' : null"
				/>
			</div>
			<div v-else-if="state == 'Site Created'">
				<div class="text-center text-base text-gray-900">
					Your site is ready. Logging in...
				</div>
			</div>
		</LoginBox>
	</div>
</template>
<script setup>
import { ref, computed } from 'vue';
import { ErrorMessage, FormControl, Progress, createResource } from 'frappe-ui';
import LoginBox from '../partials/LoginBox.vue';
import { useElementSize } from '@vueuse/core';
import { validateSubdomain } from '@/utils';

const props = defineProps(['product']);
const state = ref('Pending'); // Pending, Wait for Site, Site Created

const saasProduct = createResource({
	url: 'press.api.saas.get_saas_product_info',
	params: {
		product: props.product
	},
	auto: true,
	onSuccess(data) {
		if (data?.site_request) {
			state.value = data.site_request.status;
			if (state.value === 'Wait for Site') {
				siteProgress.reload();
			}
		}
	}
});

const subdomain = ref(null);
const createSite = createResource({
	url: 'press.api.saas.create_site',
	makeParams() {
		return {
			product: props.product,
			subdomain: subdomain.value,
			site_request: saasProduct.data.site_request
		};
	},
	validate() {
		return validateSubdomain(subdomain.value);
	},
	onSuccess() {
		state.value = 'Wait for Site';
		siteProgress.reload();
	}
});

const siteProgress = createResource({
	url: 'press.api.saas.get_site_progress',
	makeParams() {
		return {
			site_request: saasProduct.data.site_request.name
		};
	},
	onSuccess(data) {
		if (data.progress == 100) {
			state.value = 'Site Created';
			loginToSite.submit();
		} else {
			setTimeout(() => {
				siteProgress.reload();
			}, 2000);
		}
	}
});

const loginToSite = createResource({
	url: 'press.api.saas.login_to_site',
	makeParams() {
		return {
			site_request: saasProduct.data.site_request.name
		};
	},
	onSuccess(data) {
		if (data?.sid && data?.site) {
			window.location.href = `https://${data.site}/desk?sid=${data.sid}`;
		}
	}
});

const domainSuffix = ref(null);
const { width } = useElementSize(domainSuffix);
const inputPaddingRight = computed(() => {
	return width.value + 10 + 'px';
});
</script>
<style scoped>
.subdomain :deep(input) {
	padding-right: v-bind(inputPaddingRight);
}
</style>
