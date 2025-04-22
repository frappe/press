<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="$resources.saasProduct.loading || $resources.siteRequest.loading"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50" v-else>
		<div class="w-full overflow-auto">
			<LoginBox
				v-if="$resources?.siteRequest?.doc?.status === 'Site Created'"
				title="Site created successfully"
				:subtitle="`Your trial site is ready at
					${$resources?.siteRequest?.doc?.domain || $resources?.siteRequest?.doc?.site}`"
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
				<div>
					<div
						class="mb-4 mt-16 flex flex-col items-center justify-center space-y-4"
					>
						<Button
							variant="solid"
							class="w-2/5"
							icon-right="external-link"
							@click="loginToSite"
							:loading="this.$resources?.siteRequest?.getLoginSid.loading"
						>
							Log In
						</Button>
					</div>
				</div>
				<ErrorMessage
					class="w-full text-center"
					:message="this.$resources?.siteRequest?.getLoginSid.error"
				/>
				<template v-slot:footer>
					<div
						class="mt-2 flex w-full items-center justify-center text-sm text-gray-600"
					>
						Powered by Frappe Cloud
					</div>
				</template>
			</LoginBox>
			<LoginBox
				v-else-if="this.$resources?.siteRequest?.doc?.status === 'Error'"
				title="Site creation failed"
				:subtitle="
					this.$resources?.siteRequest?.doc?.domain ||
					this.$resources?.siteRequest?.doc?.site
				"
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
					<div class="flex h-40 flex-col items-center justify-center px-10">
						<div class="text-center text-base leading-5 text-gray-800">
							<p>It looks like something went wrong</p>
							<p>
								Contact
								<a href="mailto:support@frappe.io" class="underline"
									>support@frappe.io</a
								><br />
								to resolve the issue
							</p>
						</div>
					</div>
				</template>
				<template v-slot:footer>
					<div
						class="mt-2 flex w-full items-center justify-center text-sm text-gray-600"
					>
						Powered by Frappe Cloud
					</div>
				</template>
			</LoginBox>
			<LoginBox
				v-else
				title="Creating your site"
				:subtitle="
					this.$resources?.siteRequest?.doc?.domain ||
					this.$resources?.siteRequest?.doc?.site
				"
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
					<div class="flex h-40 items-center justify-center">
						<Progress
							class="px-10"
							size="md"
							:value="progressCount"
							:label="currentBuildStep"
						/>
					</div>
				</template>
				<template v-slot:footer>
					<div
						class="mt-2 flex w-full items-center justify-center text-sm text-gray-600"
					>
						Powered by Frappe Cloud
					</div>
				</template>
			</LoginBox>
		</div>
	</div>
</template>
<script>
import LoginBox from '../../components/auth/LoginBox.vue';
import { Progress } from 'frappe-ui';

export default {
	name: 'SignupLoginToSite',
	props: ['productId'],
	components: {
		LoginBox,
		Progress,
	},
	data() {
		return {
			product_trial_request: this.$route.query.product_trial_request,
			progressCount: 0,
			currentBuildStep: 'Preparing for build',
		};
	},
	resources: {
		saasProduct() {
			return {
				type: 'document',
				doctype: 'Product Trial',
				name: this.productId,
				auto: true,
			};
		},
		siteRequest() {
			return {
				type: 'document',
				doctype: 'Product Trial Request',
				name: this.product_trial_request,
				realtime: true,
				auto: true,
				onSuccess(doc) {
					if (
						doc.status == 'Wait for Site' ||
						doc.status == 'Prefilling Setup Wizard'
					) {
						this.$resources.siteRequest.getProgress.reload();
					}
				},
				whitelistedMethods: {
					getProgress: {
						method: 'get_progress',
						makeParams() {
							return {
								current_progress:
									this.$resources.siteRequest.getProgress.data?.progress || 0,
							};
						},
						onSuccess: (data) => {
							const currentStepMap = {
								'Wait for Site': 'Creating your site',
								'New Site': 'Creating your site',
								'Prefilling Setup Wizard': 'Setting up your site',
								'Update Site Configuration': 'Setting up your site',
								'Enable Scheduler': 'Setting up your site',
								'Bench Setup NGINX': 'Setting up your site',
								'Reload NGINX': 'Setting up your site',
							};

							this.currentBuildStep =
								currentStepMap[data.current_step] ||
								data.current_step ||
								this.currentBuildStep;
							this.progressCount += 1;

							if (
								!(
									this.$resources.siteRequest.getProgress.error &&
									this.progressCount <= 10
								)
							) {
								this.progressCount = Math.round(data.progress * 10) / 10;
								setTimeout(() => {
									this.$resources.siteRequest.getProgress.reload();
								}, 2000);
							}
						},
					},
					getLoginSid: {
						method: 'get_login_sid',
						onSuccess(data) {
							const sid = data;
							const redirectRoute =
								this.$resources?.saasProduct?.doc?.redirect_to_after_login ??
								'/desk';
							const loginURL = `https://${this.$resources.siteRequest.doc.domain}${redirectRoute}?sid=${sid}`;
							window.open(loginURL, '_blank');
						},
					},
				},
			};
		},
	},
	computed: {
		saasProduct() {
			return this.$resources.saasProduct.doc;
		},
	},
	methods: {
		loginToSite() {
			this.$resources.siteRequest.getLoginSid.submit();
		},
	},
};
</script>
