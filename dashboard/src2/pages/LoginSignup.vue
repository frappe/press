<template>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50">
		<div class="w-full overflow-auto">
			<LoginBox
				:title="title"
				:class="{ 'pointer-events-none': $resources.signup.loading }"
			>
				<template v-slot:default>
					<div v-if="!(resetPasswordEmailSent || accountRequestCreated)">
						<form class="flex flex-col" @submit.prevent="submitForm">
							<!-- 2FA Section -->
							<template v-if="is2FA">
								<FormControl
									label="2FA Code from your Authenticator App"
									placeholder="123456"
									v-model="twoFactorCode"
									required
								/>
								<Button
									class="mt-4"
									:loading="
										$resources.verify2FA.loading ||
										$session.login.loading ||
										$resources.resetPassword.loading
									"
									variant="solid"
									@click="
										$resources.verify2FA.submit({
											user: email,
											totp_code: twoFactorCode
										})
									"
								>
									Verify
								</Button>
								<ErrorMessage
									class="mt-2"
									:message="$resources.verify2FA.error"
								/>
							</template>

							<!-- Forgot Password Section -->
							<template v-else-if="hasForgotPassword">
								<FormControl
									label="Email"
									type="email"
									placeholder="johndoe@mail.com"
									autocomplete="email"
									v-model="email"
									required
								/>
								<router-link
									class="mt-2 text-sm"
									v-if="hasForgotPassword"
									:to="{
										name: 'Login',
										query: { ...$route.query, forgot: undefined }
									}"
								>
									I remember my password
								</router-link>
								<Button
									class="mt-4"
									:loading="$resources.resetPassword.loading"
									variant="solid"
								>
									Reset Password
								</Button>
							</template>

							<!-- Login Section -->
							<template v-else-if="isLogin">
								<FormControl
									label="Email"
									placeholder="johndoe@mail.com"
									autocomplete="email"
									v-model="email"
									required
								/>
								<FormControl
									v-if="!isOauthLogin"
									class="mt-4"
									label="Password"
									type="password"
									placeholder="•••••"
									v-model="password"
									name="password"
									autocomplete="current-password"
									required
								/>
								<div class="mt-2" v-if="isLogin && !isOauthLogin">
									<router-link
										class="text-sm"
										:to="{
											name: 'Login',
											query: { ...$route.query, forgot: 1 }
										}"
									>
										Forgot Password?
									</router-link>
								</div>
								<Button v-if="!isOauthLogin" class="mt-4" variant="solid">
									Log in with email
								</Button>
								<Button v-else class="mt-4" variant="solid">
									Log in with {{ oauthProviderName }}
								</Button>
								<ErrorMessage
									class="mt-2"
									:message="
										$session.login.error || $resources.is2FAEnabled.error
									"
								/>
							</template>

							<!-- Signup Section -->
							<template v-else>
								<FormControl
									label="Email"
									type="email"
									placeholder="johndoe@mail.com"
									autocomplete="email"
									v-model="email"
									required
								/>
								<Button
									class="mt-2"
									:loading="$resources.signup.loading"
									variant="solid"
								>
									Sign up with email
								</Button>
							</template>

							<ErrorMessage class="mt-2" :message="error" />
						</form>
						<div
							class="flex flex-col"
							v-if="!hasForgotPassword && !isOauthLogin && !is2FA"
						>
							<div class="-mb-2 mt-6 border-t text-center">
								<div class="-translate-y-1/2 transform">
									<span
										class="relative bg-white px-2 text-sm font-medium leading-8 text-gray-800"
									>
										Or continue with
									</span>
								</div>
							</div>
							<Button
								variant="solid"
								:loading="$resources.googleLogin.loading"
								@click="$resources.googleLogin.submit()"
							>
								<div class="flex items-center">
									<GoogleIconSolid class="w-4" />
									<span class="ml-2">Google</span>
								</div>
							</Button>
							<div
								class="mt-6 text-center"
								v-if="!(accountRequestCreated || resetPasswordEmailSent)"
							>
								<router-link
									class="text-center text-base font-medium text-gray-900 hover:text-gray-700"
									:to="{
										name: $route.name == 'Login' ? 'Signup' : 'Login',
										query: { ...$route.query, forgot: undefined }
									}"
								>
									{{
										$route.name == 'Login'
											? 'New member? Create a new account.'
											: 'Already have an account? Log in.'
									}}
								</router-link>
							</div>
						</div>
					</div>
					<div v-else-if="accountRequestCreated">
						<form class="flex flex-col">
							<FormControl
								label="Email"
								type="email"
								placeholder="johndoe@mail.com"
								autocomplete="email"
								v-model="email"
								required
							/>
							<FormControl
								label="Verification Code"
								type="text"
								class="mt-4"
								placeholder="5 digit verification code"
								maxlength="5"
								v-model="otp"
								required
							/>
							<ErrorMessage
								class="mt-2"
								:message="$resources.verifyOTP.error"
							/>
							<Button
								class="mt-4"
								variant="solid"
								:loading="$resources.verifyOTP.loading"
								@click="$resources.verifyOTP.submit()"
							>
								Verify
							</Button>
							<Button
								class="mt-2"
								variant="outline"
								:loading="$resources.resendOTP.loading"
								@click="$resources.resendOTP.submit()"
							>
								Didn't receive OTP? Resend
							</Button>
						</form>
						<div class="mt-6 text-center">
							<router-link
								class="text-center text-base font-medium text-gray-900 hover:text-gray-700"
								:to="{
									name: $route.name == 'Login' ? 'Signup' : 'Login',
									query: { ...$route.query, forgot: undefined }
								}"
							>
								{{
									$route.name == 'Login'
										? 'New member? Create a new account.'
										: 'Already have an account? Log in.'
								}}
							</router-link>
						</div>
					</div>
					<div
						class="text-p-base text-gray-700"
						v-else-if="resetPasswordEmailSent"
					>
						<p>
							We have sent an email to
							<span class="font-semibold">{{ email }}</span
							>. Please click on the link received to reset your password.
						</p>
					</div>
				</template>
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
			</LoginBox>
		</div>
	</div>
</template>

<script>
import LoginBox from '../components/auth/LoginBox.vue';
import GoogleIconSolid from '@/components/icons/GoogleIconSolid.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'Signup',
	components: {
		LoginBox,
		GoogleIconSolid
	},
	data() {
		return {
			email: '',
			account_request: '',
			accountRequestCreated: false,
			otp: '',
			twoFactorCode: '',
			password: null,
			resetPasswordEmailSent: false
		};
	},
	mounted() {
		this.email = localStorage.getItem('login_email');
		if (window.posthog?.__loaded) {
			window.posthog.identify(this.email || window.posthog.get_distinct_id(), {
				app: 'frappe_cloud',
				action: 'login_signup'
			});
			window.posthog.startSessionRecording();
		}
	},
	unmounted() {
		if (window.posthog?.__loaded && window.posthog.sessionRecordingStarted()) {
			window.posthog.stopSessionRecording();
		}
	},
	watch: {
		email() {
			this.resetSignupState();
		}
	},
	resources: {
		signup() {
			return {
				url: 'press.api.account.signup',
				params: {
					email: this.email,
					referrer: this.getReferrerIfAny(),
					product: this.$route.query.product
				},
				onSuccess(account_request) {
					this.account_request = account_request;
					this.accountRequestCreated = true;
					toast.success('OTP sent to your email');
				},
				onError: this.onSignupError.bind(this)
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
					window.open(`/dashboard/setup-account/${key}`, '_self');
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
		oauthLogin() {
			return {
				url: 'press.api.oauth.oauth_authorize_url',
				onSuccess(url) {
					localStorage.setItem('login_email', this.email);
					window.location.href = url;
				}
			};
		},
		googleLogin() {
			return {
				url: 'press.api.google.login',
				makeParams() {
					return {
						product: this.$route.query.product
					};
				},
				onSuccess(url) {
					window.location.href = url;
				}
			};
		},
		resetPassword() {
			return {
				url: 'press.api.account.send_reset_password_email',
				onSuccess() {
					this.resetPasswordEmailSent = true;
				}
			};
		},
		signupSettings() {
			return {
				url: 'press.api.account.signup_settings',
				params: {
					product: this.$route.query.product
				},
				auto: true
			};
		},
		is2FAEnabled() {
			return {
				url: 'press.api.account.is_2fa_enabled'
			};
		},
		verify2FA() {
			return {
				url: 'press.api.account.verify_2fa',
				onSuccess: async () => {
					if (this.isLogin) {
						await this.login();
					} else if (this.hasForgotPassword) {
						await this.$resources.resetPassword.submit({
							email: this.email
						});
					}
				}
			};
		}
	},
	methods: {
		resetSignupState() {
			if (
				!this.isLogin &&
				!this.hasForgotPassword &&
				this.accountRequestCreated
			) {
				this.accountRequestCreated = false;
				this.account_request = '';
				this.otp = '';
			}
		},
		async submitForm() {
			if (this.isLogin) {
				if (this.isOauthLogin) {
					this.$resources.oauthLogin.submit({
						provider: this.socialLoginKey
					});
				} else if (this.email && this.password) {
					await this.$resources.is2FAEnabled.submit(
						{ user: this.email },
						{
							onSuccess: async two_factor_enabled => {
								if (two_factor_enabled) {
									this.$router.push({
										name: 'Login',
										query: {
											two_factor: 1
										}
									});
								} else {
									await this.login();
								}
							}
						}
					);
				}
			} else if (this.hasForgotPassword) {
				await this.$resources.is2FAEnabled.submit(
					{ user: this.email },
					{
						onSuccess: async two_factor_enabled => {
							if (two_factor_enabled) {
								this.$router.push({
									name: 'Login',
									query: {
										two_factor: 1,
										forgot: 1
									}
								});
							} else {
								await this.$resources.resetPassword.submit({
									email: this.email
								});
							}
						}
					}
				);
			} else {
				this.$resources.signup.submit();
			}
		},
		getReferrerIfAny() {
			const params = location.search;
			const searchParams = new URLSearchParams(params);
			return searchParams.get('referrer');
		},
		async login() {
			await this.$session.login.submit(
				{
					email: this.email,
					password: this.password
				},
				{
					onSuccess: res => {
						let loginRoute = `/dashboard${res.dashboard_route || '/'}`;
						if (this.$route.query.product) {
							loginRoute = `/dashboard/app-trial/setup/${this.$route.query.product}`;
						}
						localStorage.setItem('login_email', this.email);
						window.location.href = loginRoute;
					},
					onError: err => {
						if (this.$route.name === 'Login' && this.$route.query.two_factor) {
							this.$router.push({
								name: 'Login',
								query: {
									two_factor: undefined
								}
							});
							this.twoFactorCode = '';
						}
					}
				}
			);
		},
		onSignupError(error) {
			if (error?.exc_type !== 'ValidationError') {
				return;
			}
			let errorMessage = '';
			if ((error?.messages ?? []).length) {
				errorMessage = error?.messages?.[0];
			}
			// check if error message has `is already registered` substring
			if (errorMessage.includes('is already registered')) {
				localStorage.setItem('login_email', this.email);
				this.$router.push({
					name: 'Login'
				});
			}
		}
	},
	computed: {
		error() {
			if (this.$resources.signup.error) {
				return this.$resources.signup.error;
			}

			if (this.$resources.resetPassword.error) {
				return this.$resources.resetPassword.error;
			}
		},
		saasProduct() {
			return this.$resources.signupSettings.data?.product_trial;
		},
		isLogin() {
			return this.$route.name == 'Login' && !this.$route.query.forgot;
		},
		hasForgotPassword() {
			return this.$route.name == 'Login' && this.$route.query.forgot;
		},
		is2FA() {
			return this.$route.name == 'Login' && this.$route.query.two_factor;
		},
		emailDomain() {
			return this.email?.includes('@') ? this.email?.split('@').pop() : '';
		},
		isOauthLogin() {
			return (
				this.oauthEmailDomains.has(this.emailDomain) &&
				this.emailDomain.length > 0
			);
		},
		oauthProviders() {
			const domains = this.$resources.signupSettings.data?.oauth_domains;
			let providers = {};

			if (domains) {
				domains.map(
					d =>
						(providers[d.email_domain] = {
							social_login_key: d.social_login_key,
							provider_name: d.provider_name
						})
				);
			}

			return providers;
		},
		oauthEmailDomains() {
			return new Set(Object.keys(this.oauthProviders));
		},
		socialLoginKey() {
			return this.oauthProviders[this.emailDomain].social_login_key;
		},
		oauthProviderName() {
			return this.oauthProviders[this.emailDomain].provider_name;
		},
		title() {
			if (this.hasForgotPassword) {
				return 'Reset password';
			} else if (this.isLogin) {
				if (this.saasProduct) {
					return `Sign in to your account to start using ${this.saasProduct.title}`;
				}
				return 'Sign in to your account';
			} else {
				if (this.saasProduct) {
					return `Sign up to create ${this.saasProduct.title} site`;
				}
				return 'Create a new account';
			}
		}
	}
};
</script>
