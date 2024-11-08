<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="$resources.signupSettings.loading"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50" v-else>
		<div class="w-full overflow-auto">
			<LoginBox
				title="Get started in minutes"
				subtitle="14 days free trial, no credit card required."
				:class="{ 'pointer-events-none': $resources.signup?.loading }"
				:logo="saasProduct?.logo"
			>
				<template v-slot:default>
					<form class="flex flex-col" @submit.prevent="submitForm">
						<!-- Fields -->
						<FormControl
							label="Country"
							type="select"
							placeholder="Select your country"
							autocomplete="country"
							variant="outline"
							:options="countries"
							v-model="country"
							required
						/>
						<FormControl
							class="mt-5"
							label="Full Name"
							type="full_name"
							placeholder="John Doe"
							variant="outline"
							autocomplete="name"
							v-model="full_name"
							required
						/>
						<FormControl
							class="mt-5"
							label="Email"
							type="email"
							placeholder="johndoe@mail.com"
							variant="outline"
							autocomplete="email"
							v-model="email"
							required
						/>
						<FormControl
							v-if="account_request_created"
							label="Verification Code (Sent to your email)"
							type="text"
							class="mt-5"
							placeholder="5 digit verification code"
							maxlength="5"
							v-model="otp"
							required
						/>
						<div
							class="mt-5 flex items-center text-base leading-4"
							v-if="!account_request_created"
						>
							<FormControl
								type="checkbox"
								v-model="terms_accepted"
								class="mr-1"
							/>
							I agree to Frappe&nbsp;
							<Link href="https://frappecloud.com/terms" target="_blank">
								TC </Link
							>,&nbsp;
							<Link href="https://frappecloud.com/privacy" target="_blank">
								Privacy Policy
							</Link>
							&nbsp;&&nbsp;
							<Link
								href="https://frappecloud.com/cookie-policy"
								target="_blank"
							>
								Cookie Policy
							</Link>
						</div>
						<!-- Error Message -->
						<ErrorMessage class="mt-2" :message="error" />
						<!-- Buttons -->
						<Button
							v-if="!account_request_created"
							class="mt-8"
							:loading="$resources.signup?.loading"
							variant="solid"
						>
							Sign up with email
						</Button>
						<Button
							v-if="account_request_created"
							class="mt-4"
							variant="solid"
							:loading="$resources.verifyOTP?.loading"
							@click.prevent="$resources.verifyOTP.submit()"
						>
							Verify & Next
						</Button>
						<Button
							v-if="account_request_created"
							class="mt-2"
							variant="outline"
							:loading="$resources.resendOTP?.loading"
							@click.prevent="$resources.resendOTP.submit()"
						>
							Didn't receive any mail ? Resend
						</Button>
					</form>
				</template>
			</LoginBox>
		</div>
	</div>
</template>
<script>
import { Spinner } from 'frappe-ui';
import LoginBox from '../../components/auth/SaaSLoginBox.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'AppTrialSignup',
	props: ['productId'],
	components: {
		LoginBox,
		Spinner
	},
	data() {
		return {
			email: '',
			full_name: '',
			country: null,
			otp: '',
			account_request: '',
			account_request_created: false,
			terms_accepted: false
		};
	},
	mounted() {
		setTimeout(() => {
			if (window.posthog?.__loaded) {
				window.posthog.identify(window.posthog.get_distinct_id(), {
					app: 'frappe_cloud',
					action: 'saas_signup',
					saas_app: this.productId
				});
				if (!window.posthog.sessionRecordingStarted()) {
					window.posthog.startSessionRecording();
				}
			}
		}, 3000);
	},
	resources: {
		signup() {
			return {
				url: 'press.api.saas.signup',
				params: {
					email: this.email,
					full_name: this.full_name,
					country: this.country,
					product: this.productId,
					referrer: this.getReferrerIfAny(),
					terms_accepted: this.terms_accepted
				},
				validate() {
					if (!this.terms_accepted) {
						throw new Error('Please accept the terms of service');
					}
				},
				onSuccess(account_request) {
					this.account_request = account_request;
					this.account_request_created = true;
				}
			};
		},
		verifyOTP() {
			return {
				url: 'press.api.account.verify_otp',
				params: {
					account_request: this.account_request,
					otp: this.otp
				},
				onSuccess(key) {
					window.open(
						`/api/method/press.api.saas.setup_account_product_trial?key=${key}`,
						'_self'
					);
				}
			};
		},
		resendOTP() {
			return {
				url: 'press.api.account.resend_otp',
				params: {
					account_request: this.account_request
				},
				onSuccess() {
					this.otp = '';
					toast.success('Resent OTP to your email');
				}
			};
		},
		signupSettings() {
			return {
				url: 'press.api.account.signup_settings',
				params: {
					product: this.productId,
					fetch_countries: true,
					timezone: window.Intl
						? Intl.DateTimeFormat().resolvedOptions().timeZone
						: null
				},
				auto: true,
				onSuccess(res) {
					if (res && res.country) {
						this.country = res.country;
					}
				}
			};
		}
	},
	watch: {
		email() {
			this.resetSignupState();
		},
		full_name() {
			this.resetSignupState();
		},
		country() {
			this.resetSignupState();
		}
	},
	methods: {
		getReferrerIfAny() {
			const params = location.search;
			const searchParams = new URLSearchParams(params);
			return searchParams.get('referrer');
		},
		resetSignupState() {
			if (!this.account_request_created) {
				return;
			}
			this.account_request_created = false;
			this.account_request = '';
			this.otp = '';
		},
		submitForm() {
			this.$resources.signup.submit();
		}
	},
	computed: {
		error() {
			if (this.$resources.signup?.error) {
				return this.$resources.signup.error;
			}

			if (this.$resources.resetPassword?.error) {
				return this.$resources.resetPassword.error;
			}

			if (this.$resources.verifyOTP?.error) {
				return this.$resources.verifyOTP.error;
			}
		},
		saasProduct() {
			return this.$resources.signupSettings.data?.product_trial;
		},
		countries() {
			return this.$resources.signupSettings.data?.countries || [];
		}
	}
};
</script>
