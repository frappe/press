<template>
	<div class="min-h-screen bg-gray-50" v-if="siteRequest.doc && saasProduct">
		<LoginBox
			:title="siteRequest.doc.status == 'Pending' ? 'Create your site' : ''"
		>
			<template #logo>
				<div class="mx-auto">
					<div class="flex items-center justify-center space-x-2">
						<img :src="saasProduct.logo" :alt="saasProduct.title" class="h-7" />
						<h1 class="text-center text-2xl font-semibold tracking-tight">
							{{ saasProduct.title }}
						</h1>
					</div>
					<div class="mt-2 text-base text-gray-700">
						Powered by Frappe Cloud
					</div>
				</div>
			</template>
			<div class="space-y-3" v-if="siteRequest.doc.status == 'Pending'">
				<FormControl
					label="Your Email"
					:modelValue="$team.doc.user"
					:disabled="true"
				/>
				<FormControl
					class="subdomain mt-2"
					label="Site Name"
					v-model="subdomain"
					@keydown.enter="siteRequest.createSite.submit()"
				>
					<template #suffix>
						<div
							ref="domainSuffix"
							v-element-size="onResize"
							class="flex select-none items-center text-base text-gray-600"
						>
							.{{ saasProduct.domain || 'frappe.cloud' }}
						</div>
					</template>
				</FormControl>
				<ErrorMessage :message="siteRequest.createSite.error" />
				<Button
					class="w-full"
					variant="solid"
					@click="siteRequest.createSite.submit()"
					:loading="siteRequest.createSite.loading"
				>
					Create
				</Button>
			</div>
			<div v-else-if="siteRequest.doc.status == 'Wait for Site'">
				<Progress
					label="Creating site"
					:value="siteRequest.getProgress.data?.progress || 0"
					size="md"
				/>
				<ErrorMessage
					:message="
						siteRequest.getProgress.data?.error ? 'An error occurred' : null
					"
				/>
			</div>
			<div v-else-if="siteRequest.doc.status == 'Site Created'">
				<div class="text-base text-gray-900">
					Your site
					<span class="font-semibold text-gray-900">{{
						siteRequest.doc.site
					}}</span>
					is ready.
				</div>
				<div class="py-3 text-base text-gray-900">
					<Button
						:loading="siteRequest.getLoginSid.loading"
						:link="
							siteRequest.getLoginSid.data
								? `https://${siteRequest.doc.site}/desk?sid=${siteRequest.getLoginSid.data.sid}`
								: null
						"
					>
						<template #prefix>
							<i-lucide-external-link class="h-4 w-4 text-gray-700" />
						</template>
						{{
							siteRequest.getLoginSid.loading
								? 'Generating login URL...'
								: `Login to your site`
						}}
					</Button>
				</div>
				<div>
					<Button @click="goToDashboard">
						<template #prefix>
							<i-lucide-home class="h-4 w-4 text-gray-700" />
						</template>
						Go to Frappe Cloud Dashboard
					</Button>
				</div>
			</div>
		</LoginBox>
	</div>
</template>
<script>
import { ErrorMessage, Progress } from 'frappe-ui';
import LoginBox from '@/views/partials/LoginBox.vue';
import { vElementSize } from '@vueuse/components';
import { validateSubdomain } from '@/utils';

export default {
	name: 'NewAppSite',
	directives: {
		'element-size': vElementSize
	},
	components: {
		LoginBox
	},
	data() {
		return {
			subdomain: null,
			inputPaddingRight: null
		};
	},
	resources: {
		siteRequest() {
			if (!this.$team?.doc?.onboarding.saas_site_request) return;
			return {
				type: 'document',
				doctype: 'SaaS Product Site Request',
				name: this.$team.doc.onboarding.saas_site_request,
				realtime: true,
				onSuccess(doc) {
					if (doc.status == 'Wait for Site') {
						this.siteRequest.getProgress.reload();
					}
				},
				whitelistedMethods: {
					createSite: {
						method: 'create_site',
						makeParams() {
							return { subdomain: this.subdomain };
						},
						validate() {
							return validateSubdomain(this.subdomain);
						},
						onSuccess() {
							this.siteRequest.getProgress.reload();
						}
					},
					getProgress: {
						method: 'get_progress',
						makeParams() {
							return {
								current_progress:
									this.siteRequest.getProgress.data?.progress || 0
							};
						},
						onSuccess(data) {
							if (data.progress == 100) {
								this.siteRequest.getLoginSid.fetch();
							} else {
								setTimeout(() => {
									this.siteRequest.getProgress.reload();
								}, 2000);
							}
						}
					},
					getLoginSid: 'get_login_sid'
				}
			};
		}
	},
	methods: {
		onResize({ width }) {
			this.inputPaddingRight = width + 10 + 'px';
		},
		goToDashboard() {
			window.location.reload();
		}
	},
	computed: {
		siteRequest() {
			return this.$resources.siteRequest;
		},
		saasProduct() {
			return this.$resources.siteRequest.doc.saas_product;
		}
	}
};
</script>
<style scoped>
.subdomain :deep(input) {
	padding-right: v-bind(inputPaddingRight);
}
</style>
