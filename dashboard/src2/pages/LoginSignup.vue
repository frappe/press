<template>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50">
		<div class="w-full overflow-auto">
			<LoginBox
				:title="title"
				:class="{ 'pointer-events-none': $resources.signup.loading }"
			>
				<template v-slot:default>
					<div v-if="!(resetPasswordEmailSent || otpRequested)">
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
											totp_code: twoFactorCode,
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
										query: { ...$route.query, forgot: undefined },
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
									:disabled="otpSent && !usePassword"
									required
								/>

								<!-- Password Authentication -->
								<template v-if="!isOauthLogin && usePassword">
									<FormControl
										class="mt-4"
										label="Password"
										type="password"
										placeholder="•••••"
										v-model="password"
										name="password"
										autocomplete="current-password"
										required
									/>
									<div class="mt-2 flex flex-col gap-2">
										<router-link
											class="text-sm"
											:to="{
												name: 'Login',
												query: { ...$route.query, forgot: 1 },
											}"
										>
											Forgot Password?
										</router-link>
									</div>
									<Button
										class="mt-4"
										variant="solid"
										:loading="$session.login.loading"
									>
										Log In
									</Button>
								</template>

								<!-- OTP Authentication -->
								<template v-else-if="!usePassword">
									<!-- OTP Verification Input (when OTP is sent) -->
									<template v-if="otpSent">
										<FormControl
											class="mt-4"
											label="Verification Code"
											placeholder="123456"
											v-model="otp"
											required
										/>
										<div class="mt-4 space-y-2">
											<Button
												class="w-full"
												:loading="$resources.verifyOTPAndLogin.loading"
												variant="solid"
												@click="verifyOTPAndLogin"
											>
												Submit verification code
											</Button>
											<Button
												class="w-full"
												:loading="$resources.sendOTP.loading"
												variant="outline"
												:disabled="otpResendCountdown > 0"
												@click="$resources.sendOTP.submit()"
											>
												Resend verification code
												{{
													otpResendCountdown > 0
														? `in ${otpResendCountdown} seconds`
														: ''
												}}
											</Button>
										</div>
									</template>

									<!-- Initial OTP Request Button -->
									<template v-else>
										<Button
											class="mt-4"
											:loading="$resources.sendOTP.loading"
											variant="solid"
											@click="$resources.sendOTP.submit()"
										>
											Send verification code
										</Button>
									</template>
								</template>

								<!-- OAuth Authentication -->
								<template v-else>
									<Button class="mt-4" variant="solid">
										Log in with {{ oauthProviderName }}
									</Button>
								</template>

								<!-- Error Messages -->
								<ErrorMessage
									class="mt-2"
									:message="
										$session.login.error ||
										$resources.is2FAEnabled.error ||
										$resources.sendOTP.error ||
										$resources.verifyOTPAndLogin.error
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
									class="mt-4"
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
										Or
									</span>
								</div>
							</div>

							<div class="flex flex-col gap-2">
								<Button
									v-if="isLogin && !usePassword"
									:route="{
										name: 'Login',
										query: { ...$route.query, use_password: 1 },
									}"
									icon-left="key"
								>
									Continue with password
								</Button>
								<Button
									v-else-if="isLogin && usePassword"
									:route="{
										name: 'Login',
										query: { ...$route.query, use_password: undefined },
									}"
									icon-left="mail"
								>
									Continue with verification code
								</Button>
								<Button
									:loading="$resources.googleLogin.loading"
									@click="$resources.googleLogin.submit()"
								>
									<div class="flex items-center">
										<GoogleIconSolid class="w-4" />
										<span class="ml-2">Continue with Google</span>
									</div>
								</Button>
							</div>
							<div
								class="mt-6 text-center"
								v-if="!(otpRequested || resetPasswordEmailSent)"
							>
								<router-link
									class="text-center text-base font-medium text-gray-900 hover:text-gray-700"
									:to="{
										name: $route.name == 'Login' ? 'Signup' : 'Login',
										query: { ...$route.query, forgot: undefined },
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
					<div v-else-if="otpRequested">
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
								label="Verification code"
								type="text"
								class="mt-4"
								placeholder="123456"
								maxlength="6"
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
								:disabled="otpResendCountdown > 0"
							>
								Resend verification code
								{{
									otpResendCountdown > 0
										? `in ${otpResendCountdown} seconds`
										: ''
								}}
							</Button>
						</form>
						<div class="mt-6 text-center">
							<router-link
								class="text-center text-base font-medium text-gray-900 hover:text-gray-700"
								:to="{
									name: $route.name == 'Login' ? 'Signup' : 'Login',
									query: { ...$route.query, forgot: undefined },
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
				<template v-slot:footer v-if="saasProduct">
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
import LoginBox from '../components/auth/LoginBox.vue';
import GoogleIconSolid from '@/components/icons/GoogleIconSolid.vue';
import { toast } from 'vue-sonner';
import { getToastErrorMessage } from '../utils/toast';

export default {
	name: 'Signup',
	components: {
		LoginBox,
		GoogleIconSolid,
	},
	data() {
		return {
			email: '',
			account_request: '',
			otpRequested: false,
			otp: '',
			otpSent: false,
			twoFactorCode: '',
			password: null,
			otpResendCountdown: 0,
			resetPasswordEmailSent: false,
		};
	},
	mounted() {
		this.email = localStorage.getItem('login_email');
		setInterval(() => {
			if (this.otpResendCountdown > 0) {
				this.otpResendCountdown -= 1;
			}
		}, 1000);
	},
	watch: {
		email() {
			this.resetSignupState();
		},
	},
	resources: {
		signup() {
			return {
				url: 'press.api.account.signup',
				params: {
					email: this.email,
					referrer: this.getReferrerIfAny(),
					product: this.$route.query.product,
				},
				onSuccess(account_request) {
					this.account_request = account_request;
					this.otpRequested = true;
					this.otpResendCountdown = 30;
					toast.success('Verification code sent to your email');
				},
				onError: (error) => {
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

						if (this.$route.query?.product) {
							this.$router.push({
								name: 'Login',
								query: {
									redirect: `/dashboard/create-site/${this.$route.query.product}/setup`,
								},
							});
						} else {
							this.$router.push({
								name: 'Login',
							});
						}
					}
				},
			};
		},
		verifyOTP() {
			return {
				url: 'press.api.account.verify_otp',
				params: {
					account_request: this.account_request,
					otp: this.otp,
				},
				onSuccess(key) {
					window.open(`/dashboard/setup-account/${key}`, '_self');
				},
			};
		},
		resendOTP() {
			return {
				url: 'press.api.account.resend_otp',
				params: {
					account_request: this.account_request,
				},
				onSuccess() {
					this.otp = '';
					this.otpResendCountdown = 30;
					toast.success('Verification code sent to your email');
				},
				onError(err) {
					toast.error(
						getToastErrorMessage(err, 'Failed to resend verification code'),
					);
				},
			};
		},
		sendOTP() {
			return {
				url: 'press.api.account.send_otp',
				params: {
					email: this.email,
				},
				onSuccess() {
					this.otpSent = true;
					this.otpResendCountdown = 30;
					toast.success('Verification code sent to your email');
				},
				onError(err) {
					toast.error(
						getToastErrorMessage(err, 'Failed to send verification code'),
					);
				},
			};
		},
		verifyOTPAndLogin() {
			return {
				url: 'press.api.account.verify_otp_and_login',
				params: {
					email: this.email,
					otp: this.otp,
				},
				onSuccess(res) {
					this.afterLogin(res);
				},
			};
		},
		oauthLogin() {
			return {
				url: 'press.api.oauth.oauth_authorize_url',
				onSuccess(url) {
					localStorage.setItem('login_email', this.email);
					window.location.href = url;
				},
			};
		},
		googleLogin() {
			return {
				url: 'press.api.google.login',
				makeParams() {
					return {
						product: this.$route.query.product,
					};
				},
				onSuccess(url) {
					window.location.href = url;
				},
			};
		},
		resetPassword() {
			return {
				url: 'press.api.account.send_reset_password_email',
				onSuccess() {
					this.resetPasswordEmailSent = true;
				},
			};
		},
		signupSettings() {
			return {
				url: 'press.api.account.signup_settings',
				params: {
					product: this.$route.query.product,
				},
				auto: true,
			};
		},
		is2FAEnabled() {
			return {
				url: 'press.api.account.is_2fa_enabled',
			};
		},
		verify2FA() {
			return {
				url: 'press.api.account.verify_2fa',
				onSuccess: async () => {
					if (this.isLogin) {
						if (!this.usePassword) {
							await this.$resources.verifyOTPAndLogin.submit();
						} else {
							await this.login();
						}
					} else if (this.hasForgotPassword) {
						await this.$resources.resetPassword.submit({
							email: this.email,
						});
					}
				},
			};
		},
	},
	methods: {
		resetSignupState() {
			if (!this.isLogin && !this.hasForgotPassword && this.otpRequested) {
				this.otpRequested = false;
				this.account_request = '';
				this.otp = '';
			}
		},
		async submitForm() {
			if (this.isLogin) {
				if (this.isOauthLogin) {
					this.$resources.oauthLogin.submit({
						provider: this.socialLoginKey,
					});
				} else if (!this.usePassword) {
					// OTP login is handled by separate buttons
					return;
				} else if (this.email && this.password) {
					await this.checkTwoFactorAndLogin();
				}
			} else if (this.hasForgotPassword) {
				await this.checkTwoFactorAndResetPassword();
			} else {
				this.$resources.signup.submit();
			}
		},

		async checkTwoFactorAndLogin() {
			await this.$resources.is2FAEnabled.submit(
				{ user: this.email },
				{
					onSuccess: async (two_factor_enabled) => {
						if (two_factor_enabled) {
							this.$router.push({
								name: 'Login',
								query: {
									...this.$route.query,
									two_factor: 1,
								},
							});
						} else {
							await this.login();
						}
					},
				},
			);
		},

		async checkTwoFactorAndResetPassword() {
			await this.$resources.is2FAEnabled.submit(
				{ user: this.email },
				{
					onSuccess: async (two_factor_enabled) => {
						if (two_factor_enabled) {
							this.$router.push({
								name: 'Login',
								query: {
									two_factor: 1,
									forgot: 1,
								},
							});
						} else {
							await this.$resources.resetPassword.submit({
								email: this.email,
							});
						}
					},
				},
			);
		},

		verifyOTPAndLogin() {
			this.$resources.is2FAEnabled.submit(
				{ user: this.email },
				{
					onSuccess: async (two_factor_enabled) => {
						if (two_factor_enabled) {
							this.$router.push({
								name: 'Login',
								query: {
									...this.$route.query,
									two_factor: 1,
								},
							});
						} else {
							await this.$resources.verifyOTPAndLogin.submit();
						}
					},
				},
			);
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
					password: this.password,
				},
				{
					onSuccess: (res) => {
						this.afterLogin(res);
					},
					onError: (err) => {
						if (this.$route.name === 'Login' && this.$route.query.two_factor) {
							this.$router.push({
								name: 'Login',
								query: {
									two_factor: undefined,
								},
							});
							this.twoFactorCode = '';
						}
					},
				},
			);
		},
		afterLogin(res) {
			let loginRoute = `/dashboard${res.dashboard_route || '/'}`;
			// if query param redirect is present, redirect to that route
			if (this.$route.query.redirect) {
				loginRoute = this.$route.query.redirect;
			}
			localStorage.setItem('login_email', this.email);
			window.location.href = loginRoute;
		},
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
		usePassword() {
			return Boolean(this.$route.query.use_password);
		},
		oauthProviders() {
			const domains = this.$resources.signupSettings.data?.oauth_domains;
			let providers = {};

			if (domains) {
				domains.map(
					(d) =>
						(providers[d.email_domain] = {
							social_login_key: d.social_login_key,
							provider_name: d.provider_name,
						}),
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
					return `Log in to your account to start using ${this.saasProduct.title}`;
				}
				return 'Log in to your account';
			} else {
				if (this.saasProduct) {
					return `Sign up to create your ${this.saasProduct.title} site`;
				}
				return 'Create a new account';
			}
		},
	},
};
</script>
