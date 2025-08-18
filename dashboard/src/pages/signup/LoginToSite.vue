<template>
	<div
		class="flex h-screen w-screen flex-col items-center justify-center bg-gray-600 bg-opacity-50"
		v-if="
			$resources?.siteRequest?.doc?.status &&
			!['Error'].includes($resources?.siteRequest?.doc?.status)
		"
	>
		<SignupSpinner />
		<p class="text-white">
			{{
				$resources?.siteRequest?.doc?.status === 'Site Created'
					? 'Logging you in'
					: 'Completing setup'
			}}
		</p>
	</div>
	<div class="flex h-screen overflow-hidden" v-else>
		<div class="w-full overflow-auto">
			<LoginBox
				v-if="$resources?.siteRequest?.doc?.status === 'Site Created'"
				title="Site created successfully"
				:subtitle="`Your trial site is ready ats
					${$resources?.siteRequest?.doc?.domain || $resources?.siteRequest?.doc?.site}`"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="flex space-x-2">
						<img
							class="inline-block h-[38px] w-[38px] rounded-sm"
							:src="saasProduct?.logo"
						/>
					</div>
				</template>
				<div>
					<div
						class="mb-4 mt-16 flex flex-col items-center justify-center space-y-4"
					>
						<Button
							variant="solid"
							class="w-full"
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
			</LoginBox>
			<LoginBox
				v-else-if="$resources?.siteRequest?.doc?.status === 'Error'"
				title="Site creation failed"
				:subtitle="
					$resources?.siteRequest?.doc?.domain ||
					$resources?.siteRequest?.doc?.site
				"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="flex space-x-2">
						<img
							class="inline-block h-7 w-7 rounded-sm"
							:src="saasProduct?.logo"
						/>
					</div>
				</template>
				<template v-slot:default>
					<div class="flex h-40 flex-col justify-center">
						<div class="text-base leading-5 text-gray-800">
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
			</LoginBox>
		</div>
	</div>
</template>
<script>
import LoginBox from '../../components/auth/LoginBox.vue';
import Spinner from '../../components/LoginSpinner.vue';
import { Progress } from 'frappe-ui';

export default {
	name: 'SignupLoginToSite',
	props: ['productId'],
	components: {
		LoginBox,
		Progress,
		SignupSpinner: Spinner,
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
					if (doc.status == 'Site Created') this.loginToSite();
					else if (
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
							if (data.status === 'Site Created') {
								return this.loginToSite();
							}

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
									if (
										['Site Created', 'Error'].includes(
											this.$resources.siteRequest.doc.status,
										)
									)
										return;

									this.$resources.siteRequest.getProgress.reload();
								}, 2000);
							}
						},
					},
					getLoginSid: {
						method: 'get_login_sid',
						onSuccess(loginURL) {
							window.open(loginURL, '_self');
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
