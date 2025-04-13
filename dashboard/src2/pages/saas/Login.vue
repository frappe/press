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
				title="Welcome back"
				:subtitle="`Login to your ${saasProduct?.title} site`"
				:class="{ 'pointer-events-none': $resources.signup?.loading }"
				:logo="saasProduct?.logo"
			>
				<template v-slot:default>
					<form class="flex flex-col" @submit.prevent="">
						<FormControl
							class="w-full"
							label="Email"
							type="email"
							placeholder="johndoe@mail.com"
							variant="outline"
							autocomplete="email"
							v-model="email"
							required
						/>
						<FormControl
							v-if="isLoginWithEmail"
							class="mt-4 w-full"
							label="Verification Code"
							type="text"
							placeholder="5 digit verification code"
							variant="outline"
							v-model="code"
							required
						/>

						<!-- Error Message -->
						<ErrorMessage
							class="mt-2"
							:message="
								this.$resources?.sendVerificationCodeForLogin?.error ||
								this.$resources?.loginUsingCode?.error
							"
						/>
						<!-- Buttons -->
						<div
							class="mt-5 flex flex-col items-center gap-3"
							v-if="!isLoginWithEmail"
						>
							<Button
								:loading="$resources.sendVerificationCodeForLogin?.loading"
								@click="$resources.sendVerificationCodeForLogin.submit()"
								variant="solid"
								class="w-full font-medium"
								type="button"
							>
								Login with email
							</Button>
							<p v-if="isGoogleOAuthEnabled">or</p>
							<Button
								v-if="isGoogleOAuthEnabled"
								variant="subtle"
								class="w-full font-medium"
								type="button"
								:loading="$resources.signupWithOAuth?.loading"
								@click="$resources.signupWithOAuth.submit()"
							>
								<div class="flex flex-row items-center gap-1">
									<GoogleIconSolid class="w-4" />
									Login with Google
								</div>
							</Button>
						</div>
						<!-- buttons to handle email verification -->
						<div class="mt-5 flex flex-col items-center gap-2" v-else>
							<Button
								:loading="$resources.loginUsingCode?.loading || isRedirecting"
								variant="solid"
								class="w-full font-medium"
								type="full"
								@click="$resources.loginUsingCode.submit()"
							>
								Verify
							</Button>
							<Button
								:loading="$resources.loginUsingCode?.loading"
								variant="outline"
								class="w-full font-medium"
								type="button"
								@click="$resources.sendVerificationCodeForLogin.submit()"
							>
								Didn't get email? Resend
							</Button>
						</div>
					</form>

					<div class="mt-6 text-center">
						<router-link
							class="text-center text-base font-medium text-gray-900 hover:text-gray-700"
							:to="{
								name: 'SaaSSignup',
								params: $route.params,
							}"
						>
							New member? Create a new account.
						</router-link>
					</div>
				</template>
			</LoginBox>
		</div>
	</div>
</template>
<script>
import { Spinner } from 'frappe-ui';
import LoginBox from '../../components/auth/SaaSLoginBox.vue';
import GoogleIconSolid from '@/components/icons/GoogleIconSolid.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'SaaSSignup',
	props: ['productId'],
	components: {
		LoginBox,
		Spinner,
		GoogleIconSolid,
	},
	data() {
		return {
			email: '',
			code: '',
			isLoginWithEmail: false,
			isRedirecting: false,
		};
	},
	watch: {
		email() {
			this.isLoginWithEmail = false;
		},
	},
	computed: {
		saasProduct() {
			return this.$resources.signupSettings.data?.product_trial || {};
		},
		isGoogleOAuthEnabled() {
			return this.$resources.signupSettings.data?.enable_google_oauth || false;
		},
	},
	resources: {
		signupSettings() {
			return {
				url: 'press.api.account.signup_settings',
				params: {
					product: this.productId,
					fetch_countries: true,
					timezone: window.Intl
						? Intl.DateTimeFormat().resolvedOptions().timeZone
						: null,
				},
				auto: true,
				onSuccess(res) {
					if (res && res.country) {
						this.country = res.country;
					}
				},
			};
		},
		sendVerificationCodeForLogin() {
			return {
				url: 'press.api.product_trial.send_verification_code_for_login',
				params: {
					email: this.email,
					product: this.productId,
				},
				auto: false,
				onSuccess() {
					this.isLoginWithEmail = true;
					toast.success('Verification code sent to your email');
				},
			};
		},
		loginUsingCode() {
			return {
				url: 'press.api.product_trial.login_using_code',
				params: {
					email: this.email,
					product: this.productId,
					code: this.code,
				},
				auto: false,
				onSuccess: (data) => {
					this.moveToSiteLoginPage(data);
				},
			};
		},
		signupWithOAuth() {
			return {
				url: 'press.api.google.login',
				params: {
					product: this.productId,
				},
				auto: false,
				onSuccess(url) {
					window.location.href = url;
				},
			};
		},
	},
	methods: {
		loginWithEmail() {
			this.isLoginWithEmail = true;
		},
		moveToSiteLoginPage(product_trial_request) {
			this.isRedirecting = true;
			window.location.href = this.$router.resolve({
				name: 'SignupLoginToSite',
				params: {
					productId: this.productId,
				},
				query: {
					product_trial_request,
				},
			}).href;
		},
	},
};
</script>
