<template>
	<div class="flex h-screen overflow-hidden">
		<div class="w-full overflow-auto">
			<LoginBox
				:title="'Let\'s set up your site'"
				subtitle="Enter site name to set up your site"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="flex space-x-2">
						<img
							class="inline-block h-[38px] w-[38px] rounded-sm"
							:src="saasProduct?.logo"
						/>
					</div>
				</template>
				<form class="mt-6 flex flex-col" @submit.prevent="createSite">
					<div class="w-full space-y-1.5">
						<div class="flex items-center gap-2">
							<label class="block text-xs text-ink-gray-5"> Site name </label>
							<Tooltip
								text="You will be able to access your site via your site name"
							>
								<lucide-info class="h-4 w-4 text-gray-500" />
							</Tooltip>
						</div>
						<div class="col-span-2 flex w-full">
							<input
								id="subdomain"
								class="dark:[color-scheme:dark] z-10 h-7 w-full rounded rounded-r-none border border-outline-gray-2 bg-surface-white py-1.5 pl-2 pr-2 text-base text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-3 hover:shadow-sm focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
								:placeholder="
									saasProduct ? `${saasProduct?.name}-site` : 'company-name'
								"
								v-model="subdomain"
								data-record="true"
							/>
							<div
								class="flex cursor-default items-center rounded-r bg-gray-100 px-2 text-base"
							>
								.{{ domain }}
							</div>
						</div>
						<div class="mt-1">
							<div v-if="!subdomain" class="text-xs text-ink-gray-5">
								Enter a site name (5-32 chars, lowercase letters, numbers,
								hyphens).
							</div>
							<ErrorMessage v-else :message="subdomainError" />
						</div>
					</div>
					<ErrorMessage class="mt-2" :message="$resources.createSite?.error" />
					<Button
						class="mt-8 w-full"
						:disabled="
							!subdomain.length ||
							subdomainError ||
							$resources.createSite?.loading
						"
						variant="solid"
						label="Create site"
						:loading="findingClosestServer || $resources.createSite?.loading"
						:loadingText="'Creating site...'"
						type="submit"
					/>
				</form>
			</LoginBox>
		</div>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import { validateSubdomain } from '../../utils/site';
import LoginBox from '../../components/auth/LoginBox.vue';

export default {
	name: 'SignupSetup',
	props: ['productId'],
	components: {
		LoginBox,
	},
	data() {
		return {
			progressErrorCount: 0,
			findingClosestServer: false,
			subdomain: '',
		};
	},
	resources: {
		siteRequest() {
			return {
				url: 'press.api.product_trial.get_request',
				params: {
					product: this.productId,
					account_request: this.$team.doc.account_request,
				},
				auto: !!this.saasProduct,
				initialData: {},
				onSuccess: (data) => {
					if (data?.status !== 'Pending') {
						this.$router.push({
							name: 'SignupLoginToSite',
							params: { productId: this.productId },
							query: {
								product_trial_request: data.name,
							},
						});
					}
					if (data.prefilled_subdomain) {
						this.subdomain = data.prefilled_subdomain || '';
					}
				},
				onError(error) {
					toast.error(error.messages.join('\n'));
				},
			};
		},
		saasProduct() {
			return {
				type: 'document',
				doctype: 'Product Trial',
				name: this.productId,
				auto: true,
			};
		},
		createSite() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Product Trial Request',
						dn: this.$resources.siteRequest.data.name,
						method: 'create_site',
						args: {
							subdomain: this.subdomain,
							domain: this.domain,
						},
					};
				},
				auto: false,
				onSuccess: (data) => {
					this.$router.push({
						name: 'SignupLoginToSite',
						params: { productId: this.productId },
						query: {
							product_trial_request: this.$resources.siteRequest.data.name,
						},
					});
				},
			};
		},
	},
	computed: {
		saasProduct() {
			return this.$resources.saasProduct?.doc;
		},
		domain() {
			return (
				this.$resources.siteRequest?.data?.domain || this.saasProduct?.domain
			);
		},
		subdomainError() {
			return validateSubdomain(this.subdomain);
		},
	},
	mounted() {
		this.email = localStorage.getItem('login_email');
		if (window.posthog?.__loaded) {
			window.posthog.identify(this.email || window.posthog.get_distinct_id(), {
				app: 'frappe_cloud',
				action: 'login_signup',
			});

			window.posthog.startSessionRecording();
		}
	},
	methods: {
		async createSite() {
			return this.$resources.createSite.submit();
		},
		redirectToLogin() {
			this.$router.push({
				name: 'Login',
			});
		},
	},
};
</script>
