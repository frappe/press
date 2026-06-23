<template>
	<div class="flex h-screen overflow-hidden">
		<div class="w-full overflow-auto">
			<LoginBox
				v-if="siteRequestDoc?.status === 'Error'"
				title="Site creation failed"
				:subtitle="siteRequestDoc?.domain || siteRequestDoc?.site"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="flex space-x-2">
						<img
							class="inline-block h-[38px] w-[38px] rounded-sm"
							:src="saasProduct?.logo"
						/>
					</div>
				</template>
				<template v-slot:default>
					<div class="flex h-40 flex-col justify-center">
						<div class="text-base leading-5 text-ink-gray-8">
							<p>It looks like something went wrong!</p>
							<p class="">
								Contact
								<a href="mailto:support@frappe.io" class="underline">
									support@frappe.io
								</a>
								to resolve the issue
							</p>
						</div>
					</div>
				</template>
			</LoginBox>
			<LoginBox
				v-else
				title="Let's set up your site"
				:subtitle="siteRequestDoc?.domain || siteRequestDoc?.site"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="flex space-x-2">
						<img
							class="inline-block h-[38px] w-[38px] rounded-sm"
							:src="saasProduct?.logo"
						/>
					</div>
				</template>
				<template v-slot:default>
					<div class="mt-12 flex flex-col items-center justify-center">
						<Progress
							size="lg"
							:value="progressCount"
							:label="currentBuildStep"
						/>
						<div
							class="flex w-full items-center space-x-2 pt-4 text-sm text-ink-gray-6"
						>
							<lucide-info class="h-4 w-4" />
							<span>{{ currentHelpText }}</span>
						</div>
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
			currentBuildStep: 'Configuring your setup',
			mockProgressTimer: null,
		};
	},
	mounted() {
		if (this.isMockMode) this.startMockProgress();
	},
	beforeUnmount() {
		clearInterval(this.mockProgressTimer);
	},
	resources: {
		saasProduct() {
			return {
				type: 'document',
				doctype: 'Product Trial',
				name: this.productId,
				auto: !this.isMockMode,
			};
		},
		siteRequest() {
			return {
				type: 'document',
				doctype: 'Product Trial Request',
				name: this.product_trial_request,
				realtime: true,
				auto: !this.isMockMode,
				onSuccess(doc) {
					if (doc.status === 'Site Created') {
						this.showCompleteProgress();
						setTimeout(() => {
							this.loginToSite();
						}, 500);
					} else if (this.isSiteProvisioning(doc.status)) {
						this.$resources.siteRequest.getProgress.reload();
					}
				},
				whitelistedMethods: {
					getProgress: {
						method: 'get_progress',
						makeParams() {
							return {
								current_progress: this.progressCount,
							};
						},
						onSuccess: (data) => {
							if (data.current_step === 'Site Created') {
								this.showCompleteProgress();
								setTimeout(() => {
									this.loginToSite();
								}, 500);
								return;
							}

							const currentStepMap = {
								'Wait for Site': 'Creating your site',
								'New Site': 'Creating your site',
								'Prefilling Setup Wizard': 'Configuring your site',
								'Adding Domain': 'Configuring your site',
								'Site Created': 'Almost there',
							};

							this.currentBuildStep =
								currentStepMap[data.current_step] ||
								data.current_step ||
								this.currentBuildStep;
							const nextProgress = Number(data.progress || 0);

							if (
								!(
									this.$resources.siteRequest.getProgress.error &&
									this.progressCount <= 10
								)
							) {
								const visibleProgress = Math.min(
									Math.max(nextProgress, this.progressCount + 0.2),
									95,
								);
								this.progressCount = Math.round(visibleProgress * 10) / 10;
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
		isMockMode() {
			return (
				this.$route.name === 'ProductTrialProgressMock' ||
				this.$route.query.mock === '1'
			);
		},
		saasProduct() {
			if (this.isMockMode) {
				return {
					logo: '/assets/press/images/frappe-cloud-logo.png',
					help_texts: [
						{ help_text: 'We are preparing your trial workspace.' },
						{ help_text: 'This preview is using local mock data.' },
						{ help_text: 'The real page updates from Agent Job progress.' },
					],
				};
			}
			return this.$resources.saasProduct.doc;
		},
		siteRequestDoc() {
			if (this.isMockMode) {
				return {
					status: 'Adding Domain',
					domain: 'acme.frappe.cloud',
					site: 'acme.frappe.cloud',
				};
			}
			return this.$resources?.siteRequest?.doc;
		},
		currentHelpText() {
			const defaultHelpTexts = [
				'Find anything with the Awesome bar!',
				'All Frappe apps are open-source!',
				'You can install more apps later!',
			];

			const productHelpTexts = this.saasProduct?.help_texts
				? this.saasProduct.help_texts.map((t) => t.help_text)
				: [];
			const helpTexts = productHelpTexts.length
				? productHelpTexts
				: defaultHelpTexts;
			const helpTextIndex = Math.floor(this.progressCount) % helpTexts.length;

			return helpTexts[helpTextIndex] || defaultHelpTexts[0];
		},
	},
	methods: {
		startMockProgress() {
			let tick = 0;
			const mockSteps = [
				'Configuring your site',
				'Configuring your domain',
				'Finalizing your setup',
				'Almost there',
			];

			this.progressCount = 18;
			this.currentBuildStep = mockSteps[0];
			this.mockProgressTimer = setInterval(() => {
				const activeStep = Math.min(Math.floor(tick / 4), mockSteps.length - 1);
				this.currentBuildStep = mockSteps[activeStep];
				this.progressCount = Math.min(95, this.progressCount + 2.4);
				tick += 1;
			}, 1000);
		},
		showCompleteProgress() {
			this.progressCount = 100;
			this.currentBuildStep = 'Almost there';
		},
		isSiteProvisioning(status) {
			return ['Wait for Site', 'Prefilling Setup Wizard', 'Adding Domain'].includes(
				status,
			);
		},
		loginToSite() {
			this.$resources.siteRequest.getLoginSid.submit();
		},
	},
};
</script>
