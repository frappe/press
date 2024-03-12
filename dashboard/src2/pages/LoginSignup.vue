<template>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50">
		<ProductSignupPitch
			v-if="saasProduct"
			:saasProduct="saasProduct"
			class="hidden w-[40%] sm:block"
		/>
		<div class="w-full overflow-auto">
			<LoginBox
				:title="title"
				:class="{ 'pointer-events-none': $resources.signup.loading }"
			>
				<div v-if="!(signupEmailSent || resetPasswordEmailSent)">
					<form class="flex flex-col" @submit.prevent="submitForm">
						<template v-if="hasForgotPassword">
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
						<template v-else-if="isLogin">
							<FormControl
								label="Email"
								placeholder="johndoe@mail.com"
								autocomplete="email"
								v-model="email"
								required
							/>
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
							<div class="mt-2" v-if="isLogin">
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
							<Button class="mt-4" variant="solid"> Log in with email </Button>
							<ErrorMessage class="mt-2" :message="$session.login.error" />
						</template>
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
						<ErrorMessage class="mt-2" :message="$resources.signup.error" />
					</form>
					<div class="flex flex-col" v-if="!hasForgotPassword">
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
							v-if="!(signupEmailSent || resetPasswordEmailSent)"
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
				<div class="text-p-base text-gray-700" v-else>
					<p v-if="signupEmailSent">
						We have sent an email to
						<span class="font-semibold">{{ email }}</span
						>. Please click on the link received to verify your email and set up
						your account.
					</p>
					<p v-if="resetPasswordEmailSent">
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
import LoginBox from '@/views/partials/LoginBox.vue';
import GoogleIconSolid from '@/components/icons/GoogleIconSolid.vue';
import ProductSignupPitch from '../components/ProductSignupPitch.vue';

export default {
	name: 'Signup',
	components: {
		LoginBox,
		GoogleIconSolid,
		ProductSignupPitch
	},
	data() {
		return {
			email: null,
			password: null,
			signupEmailSent: false,
			resetPasswordEmailSent: false
		};
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
				onSuccess() {
					this.signupEmailSent = true;
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
		async submitForm() {
			if (this.isLogin) {
				if (this.email && this.password) {
					await this.$session.login.submit(
						{
							email: this.email,
							password: this.password
						},
						{
							onSuccess: res => {
								let loginRoute = `/dashboard-beta${res.dashboard_route || '/'}`;
								if (this.$route.query.product) {
									loginRoute = `/dashboard-beta/app-trial/${this.$route.query.product}`;
								}
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
		saasProduct() {
			return this.$resources.signupSettings.data?.saas_product;
		},
		isLogin() {
			return this.$route.name == 'Login' && !this.$route.query.forgot;
		},
		hasForgotPassword() {
			return this.$route.name == 'Login' && this.$route.query.forgot;
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
