<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="$resources.saasProduct.loading"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50" v-else>
		<div class="w-full overflow-auto">
			<LoginBox
				title="Let’s set up your site"
				subtitle="Setup your default settings for your site"
				:logo="saasProduct?.logo"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="mx-auto flex items-center space-x-2">
						<img
							class="inline-block h-7 w-7 rounded-sm"
							:src="saasProduct?.logo"
						/>
						<span
							class="select-none text-xl font-semibold tracking-tight text-gray-900"
						>
							{{ saasProduct?.title }}
						</span>
					</div>
				</template>
				<template v-slot:default>
					<form class="w-full" @submit.prevent="createSite">
						<FormControl
							label="Site name (will be used to access your site)"
							v-model="siteLabel"
							variant="outline"
							class="mb-4"
						/>
						<FormControl
							label="Email address (will be your login ID)"
							:modelValue="$team.doc.user"
							:disabled="true"
							variant="outline"
							class="mb-4"
						/>
						<SaaSSignupFields
							v-if="saasProductSignupFields.length > 0"
							:fields="saasProductSignupFields"
							v-model="signupValues"
						></SaaSSignupFields>
						<ErrorMessage
							class="mt-2"
							:message="$resources.createSite?.error"
						/>
						<Button
							class="mt-8 w-full"
							variant="solid"
							type="submit"
							:loading="findingClosestServer || $resources.createSite?.loading"
							loadingText="Submitting ..."
						>
							Next
						</Button>
					</form>
				</template>
			</LoginBox>
		</div>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import LoginBox from '../../components/auth/LoginBox.vue';
import SaaSSignupFields from '../../components/SaaSSignupFields.vue';

export default {
	name: 'SaaSSignupSetup',
	props: ['productId'],
	components: {
		LoginBox,
		SaaSSignupFields,
	},
	data() {
		return {
			progressErrorCount: 0,
			findingClosestServer: false,
			closestCluster: null,
			signupValues: {},
			siteLabel: '',
			accountRequest: this.$route.query.account_request,
		};
	},
	mounted() {
		// if account request is not available
		// redirect to signup page
		if (!this.accountRequest) {
			if (this?.$session?.logoutWithoutReload?.submit) {
				this.$session.logoutWithoutReload.submit().then(() => {
					this.redirectToSignup();
				});
			} else {
				this.redirectToSignup();
			}
		} else {
			this.$resources.siteRequest.fetch();
		}
	},
	resources: {
		siteRequest() {
			return {
				url: 'press.api.product_trial.get_request',
				params: {
					product: this.productId,
					account_request: this.accountRequest,
				},
				initialData: {},
				onSuccess: (data) => {
					if (data?.status !== 'Pending') {
						this.$router.push({
							name: 'SaaSSignupLoginToSite',
							params: { productId: this.productId },
							query: {
								product_trial_request: data.name,
							},
						});
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
				onSuccess: (doc) => {
					this.siteLabel = doc.prefilled_site_label;
				},
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
							site_label: this.siteLabel,
							cluster: this.closestCluster ?? 'Default',
							signup_values: this.signupValues,
						},
					};
				},
				auto: false,
				onSuccess: (data) => {
					this.$router.push({
						name: 'SaaSSignupLoginToSite',
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
			return this.$resources.saasProduct.doc;
		},
		saasProductSignupFields() {
			return this.saasProduct?.signup_fields ?? [];
		},
	},
	methods: {
		async createSite() {
			await this.getClosestCluster();
			return this.$resources.createSite.submit();
		},
		async getClosestCluster() {
			if (this.closestCluster) return this.closestCluster;
			let proxyServers = Object.keys(this.saasProduct.proxy_servers);
			if (proxyServers.length > 0) {
				this.findingClosestServer = true;
				let promises = proxyServers.map((server) => this.getPingTime(server));
				let results = await Promise.allSettled(promises);
				let fastestServer = results.reduce((a, b) =>
					a.value.pingTime < b.value.pingTime ? a : b,
				);
				let closestServer = fastestServer.value.server;
				let closestCluster = this.saasProduct.proxy_servers[closestServer];
				if (!this.closestCluster) {
					this.closestCluster = closestCluster;
				}
				this.findingClosestServer = false;
			}
			return this.closestCluster;
		},
		async getPingTime(server) {
			let pingTime = 999999;
			try {
				let t1 = new Date().getTime();
				await fetch(`https://${server}`);
				let t2 = new Date().getTime();
				pingTime = t2 - t1;
			} catch (error) {
				console.warn(error);
			}
			return { server, pingTime };
		},
		redirectToSignup() {
			this.$router.push({
				name: 'SaaSSignup',
				params: {
					productId: this.productId,
				},
			});
		},
	},
};
</script>
