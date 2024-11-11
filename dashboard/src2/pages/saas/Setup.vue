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
			<SaaSLoginBox
				title="Let’s set up your account"
				subtitle="Setup your default settings for your account"
				:logo="saasProduct?.logo"
			>
				<template v-slot:default>
					<form class="w-full" @submit.prevent="createSite">
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
							:message="$resources.siteRequest?.createSite?.error"
						/>
						<Button
							class="mt-8 w-full"
							variant="solid"
							type="submit"
							:loading="
								findingClosestServer ||
								$resources.siteRequest?.createSite?.loading
							"
							loadingText="Submitting ..."
						>
							Next
						</Button>
					</form>
				</template>
			</SaaSLoginBox>
		</div>
	</div>
</template>
<script>
import SaaSLoginBox from '../../components/auth/SaaSLoginBox.vue';
import SaaSSignupFields from '../../components/SaaSSignupFields.vue';

export default {
	name: 'SaaSSignupSetup',
	props: ['productId'],
	components: {
		SaaSLoginBox,
		SaaSSignupFields
	},
	data() {
		return {
			progressErrorCount: 0,
			findingClosestServer: false,
			closestCluster: null,
			signupValues: {}
		};
	},
	resources: {
		getSiteRequest() {
			return {
				url: 'press.api.account.get_site_request',
				params: { product: this.productId },
				auto: true
			};
		},
		saasProduct() {
			return {
				type: 'document',
				doctype: 'Product Trial',
				name: this.productId,
				auto: true
			};
		},
		siteRequest() {
			if (!this.siteRequest && !this.siteRequest.is_pending) return;
			return {
				type: 'document',
				doctype: 'Product Trial Request',
				name: this.siteRequest.name,
				realtime: true,
				auto: true,
				onSuccess(doc) {
					if (
						doc.status == 'Wait for Site' ||
						doc.status == 'Completing Setup Wizard'
					) {
						// just redirect # todo
					}
				},
				whitelistedMethods: {
					createSite: {
						method: 'create_site',
						makeParams(params) {
							let cluster = params?.cluster;
							let signup_values = params?.signup_values;
							return {
								cluster,
								signup_values
							};
						},
						onSuccess(doc) {
							// just redirect to next page #todo
						}
					}
				}
			};
		}
	},
	methods: {
		async createSite() {
			let cluster = await this.getClosestCluster();
			return this.$resources.siteRequest.createSite.submit({
				cluster,
				signup_values: this.signupValues
			});
		},
		async getClosestCluster() {
			if (this.closestCluster) return this.closestCluster;
			let proxyServers = Object.keys(this.saasProduct.proxy_servers);
			if (proxyServers.length > 0) {
				this.findingClosestServer = true;
				let promises = proxyServers.map(server => this.getPingTime(server));
				let results = await Promise.allSettled(promises);
				let fastestServer = results.reduce((a, b) =>
					a.value.pingTime < b.value.pingTime ? a : b
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
				let r = await fetch(`https://${server}`);
				let t2 = new Date().getTime();
				pingTime = t2 - t1;
			} catch (error) {
				console.warn(error);
			}
			return { server, pingTime };
		}
	},
	computed: {
		siteRequest() {
			return this.$resources.getSiteRequest?.data ?? {};
		},
		saasProduct() {
			return this.$resources.saasProduct.doc;
		},
		saasProductSignupFields() {
			return this.saasProduct?.signup_fields ?? [];
		}
	}
};
</script>
