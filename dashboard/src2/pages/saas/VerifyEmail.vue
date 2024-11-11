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
			<SaaSLoginBox
				title="Verify your email"
				:subtitle="[
					`We sent you an email to ${email}`,
					'Check your inbox for next steps'
				]"
				:class="{ 'pointer-events-none': $resources.verifyOTP?.loading }"
				:logo="saasProduct?.logo"
			>
				<template v-slot:default>
					<form
						class="flex flex-col"
						@submit.prevent="$resources.verifyCode.submit"
					>
						<FormControl
							label="Verification Code"
							type="text"
							variant="outline"
							placeholder="5 digit verification code"
							maxlength="5"
							v-model="code"
							required
						/>
						<ErrorMessage class="mt-2" :message="$resources.verifyCode.error" />
						<Button
							class="mt-8"
							variant="solid"
							:loading="$resources.verifyCode?.loading"
							loading-text="Verifying..."
							type="submit"
						>
							Verify
						</Button>
						<Button
							class="mt-2"
							variant="outline"
							type="button"
							loading-text="Resending mail..."
							:loading="$resources.resendOTP?.loading"
							@click="$resources.resendOTP.submit()"
						>
							Email didn't arrive? Resend
						</Button>
					</form>
				</template>
			</SaaSLoginBox>
		</div>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import SaaSLoginBox from '../../components/auth/SaaSLoginBox.vue';

export default {
	name: 'SaaSVerifyEmail',
	props: ['productId'],
	components: {
		SaaSLoginBox
	},
	data() {
		return {
			account_request: this.$route.query.account_request,
			email: this.$route.query.email,
			code: ''
		};
	},
	resources: {
		signupSettings() {
			return {
				url: 'press.api.account.signup_settings',
				params: {
					product: this.productId,
					fetch_countries: false
				},
				auto: true
			};
		},
		verifyCode() {
			return {
				url: 'press.api.account.verify_otp',
				params: {
					account_request: this.account_request,
					otp: this.code
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
				},
				onerror() {
					toast.error('Failed to resend OTP');
				}
			};
		}
	},
	computed: {
		saasProduct() {
			return this.$resources.signupSettings.data?.product_trial;
		}
	}
};
</script>
