<template>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50">
		<ProductSignupPitch
			v-if="saasProduct"
			:saasProduct="saasProduct"
			class="order-1 hidden sm:block"
		/>
		<div class="w-full overflow-auto">
			<LoginBox
				:title="title"
				:class="{ 'pointer-events-none': $resources.signup.loading }"
			>
				<div v-if="!(resetPasswordEmailSent || accountRequestCreated)">
					<form class="flex flex-col" @submit.prevent="submitForm">
						<!-- Forgot Password Section -->
						<template v-if="hasForgotPassword">
							<FormControl
								label="Email"
								type="email"
								placeholder="johndoe@mail.com"
								autocomplete="email"
								:modelValue="email"
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
							<ErrorMessage class="mt-2" :message="$session.login.error" />
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
					<div class="flex flex-col" v-if="!hasForgotPassword && !isOauthLogin">
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
							label="OTP (Sent to your email)"
							type="text"
							class="mt-4"
							placeholder="5 digit OTP"
							maxlength="5"
							v-model="otp"
							required
						/>
						<ErrorMessage class="mt-2" :message="$resources.verifyOTP.error" />
						<Button
							class="mt-4"
							variant="solid"
							:loading="$resources.verifyOTP.loading"
							@click="$resources.verifyOTP.submit()"
						>
							Verify & Next
						</Button>
						<Button
							class="mt-2"
							variant="outline"
							:loading="$resources.resendOTP.loading"
							@click="$resources.resendOTP.submit()"
						>
							Didn't receive otp? Resend
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
			</LoginBox>
		</div>
	</div>
</template>

<script>
import LoginBox from '../components/auth/LoginBox.vue';
import GoogleIconSolid from '@/components/icons/GoogleIconSolid.vue';
import ProductSignupPitch from '../components/ProductSignupPitch.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'Signup',
	components: {
		LoginBox,
		GoogleIconSolid,
		ProductSignupPitch
	},
	data() {
		return {
			email: '',
			account_request: '',
			accountRequestCreated: false,
			otp: '',
			password: null,
			resetPasswordEmailSent: false
		};
	},
	mounted() {
		this.email = localStorage.getItem('login_email');
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
					product: this.$route.query.product,
					new_signup_flow: true
				},
				onSuccess(account_request) {
					this.account_request = account_request;
					this.accountRequestCreated = true;
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
				params: {
					email: this.email
				},
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
					await this.$session.login.submit(
						{
							email: this.email,
							password: this.password
						},
						{
							onSuccess: res => {
								let loginRoute = `/dashboard${res.dashboard_route || '/'}`;
								if (this.$route.query.product) {
									loginRoute = `/dashboard/app-trial/${this.$route.query.product}`;
								}
								localStorage.setItem('login_email', this.email);
								window.location.href = loginRoute;
							}
						}
					);
				}
			} else if (this.hasForgotPassword) {
				this.$resources.resetPassword.submit();
			} else {
				this.$resources.signup.submit();
			}
		},
		getReferrerIfAny() {
			const params = location.search;
			const searchParams = new URLSearchParams(params);
			return searchParams.get('referrer');
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
			} else if (this.saasProduct) {
				return `Sign in to your account to start using ${this.saasProduct.title}`;
			} else if (this.isLogin) {
				return 'Sign in to your account';
			} else {
				return 'Create a new account';
			}
		}
	}
};
</script>
