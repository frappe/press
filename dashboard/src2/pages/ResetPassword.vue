<template>
	<LoginBox
		v-if="!$resources.validateResetKey.loading && email"
		title="Set a new password for your account"
	>
		<form
			class="flex flex-col"
			@submit.prevent="$resources.resetPassword.submit()"
		>
			<div class="space-y-4">
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
			</div>
			<ErrorMessage class="mt-6" :message="$resources.resetPassword.error" />
			<Button
				class="mt-6"
				variant="solid"
				:disabled="!password"
				:loading="$resources.resetPassword.loading"
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
		LoginBox
	},
	props: ['requestKey'],
	data() {
		return {
			email: null,
			password: null
		};
	},
	resources: {
		validateResetKey() {
			return {
				url: 'press.api.account.get_user_for_reset_password_key',
				params: {
					key: this.requestKey
				},
				onSuccess(email) {
					this.email = email || null;
				},
				auto: true
			};
		},
		resetPassword() {
			return {
				url: 'press.api.account.reset_password',
				params: {
					key: this.requestKey,
					password: this.password
				},
				onSuccess() {
					window.location.reload();
				}
			};
		}
	}
};
</script>
