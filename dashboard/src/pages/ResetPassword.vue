<template>
	<LoginBox
		v-if="!$resources.validateResetKey.loading && email"
		title="Reset Password"
		subtitle="Set a new password for your account"
	>
		<form class="flex flex-col" @submit.prevent="handleSubmit">
			<div v-if="ask2FA">
				<FormControl
					label="2FA Code from your Authenticator App"
					placeholder="123456"
					v-model="twoFactorCode"
					required
				/>
			</div>
			<div v-else class="space-y-4">
				<FormControl
					label="Email"
					class="pointer-events-none"
					:modelValue="email"
					name="email"
					autocomplete="off"
					disabled
				/>
				<FormControl
					label="Password"
					type="password"
					v-model="password"
					name="password"
					autocomplete="new-password"
					required
				/>
				<FormControl
					label="Confirm Password"
					type="password"
					v-model="confirmPassword"
					name="confirm_password"
					autocomplete="new-password"
					required
				/>
			</div>
			<ErrorMessage
				class="mt-6"
				:message="
					passwordError ||
					$resources.resetPassword.error ||
					$resources.verify2FA.error ||
					$resources.is2FAEnabled.error
				"
			/>
			<Button
				class="mt-6"
				variant="solid"
				:disabled="!password"
				:loading="
					$resources.resetPassword.loading ||
					$resources.verify2FA.loading ||
					$resources.is2FAEnabled.loading
				"
				type="submit"
			>
				Submit
			</Button>
		</form>
	</LoginBox>
	<div
		class="mt-20 px-6 text-center"
		v-else-if="!$resources.validateResetKey.loading && !email"
	>
		Account Key <strong>{{ requestKey }}</strong> is invalid or expired. Go back
		to <router-link class="underline" to="/login">login</router-link>.
	</div>
</template>

<script>
import LoginBox from '../components/auth/LoginBox.vue';

export default {
	name: 'ResetPassword',
	components: {
		LoginBox,
	},
	props: ['requestKey'],
	data() {
		return {
			email: null,
			ask2FA: false,
			password: null,
			confirmPassword: null,
			passwordError: null,
		};
	},
	resources: {
		validateResetKey() {
			return {
				url: 'press.api.account.get_user_for_reset_password_key',
				params: {
					key: this.requestKey,
				},
				onSuccess(email) {
					this.email = email || null;
				},
				auto: true,
			};
		},
		resetPassword() {
			return {
				url: 'press.api.account.reset_password',
				params: {
					key: this.requestKey,
					password: this.password,
				},
				onSuccess() {
					window.location.reload();
				},
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
					await this.$resources.resetPassword.submit();
				},
			};
		},
	},
	methods: {
		handleSubmit() {
			this.passwordError = null;
			if (!this.ask2FA && this.password !== this.confirmPassword) {
				this.passwordError = 'Passwords do not match';
				return;
			}
			if (this.ask2FA) {
				this.$resources.verify2FA.submit({
					user: this.email,
					totp_code: this.twoFactorCode,
				});
			} else {
				this.$resources.is2FAEnabled.submit(
					{
						user: this.email,
					},
					{
						onSuccess: (is2FAEnabled) => {
							if (is2FAEnabled) {
								this.ask2FA = true;
							} else {
								this.$resources.resetPassword.submit();
							}
						},
					},
				);
			}
		},
	},
};
</script>
