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
				<Input
					label="Email"
					class="pointer-events-none"
					type="text"
					:modelValue="email"
					name="email"
					autocomplete="off"
					disabled
				/>
				<Input
					label="Password"
					type="password"
					v-model="password"
					name="password"
					autocomplete="new-password"
					required
				/>
			</div>
			<ErrorMessage class="mt-6" :error="$resourceErrors" />
			<Button
				class="mt-6"
				type="primary"
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
import LoginBox from './partials/LoginBox.vue';

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
				method: 'press.api.account.get_user_for_reset_password_key',
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
				method: 'press.api.account.reset_password',
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
