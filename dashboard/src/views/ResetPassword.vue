<template>
	<LoginBox v-if="!fetching && email">
		<div class="mb-8">
			<span class="text-lg">Set a new password for your account</span>
		</div>
		<form class="flex flex-col" @submit.prevent="resetPassword">
			<label class="block">
				<span class="text-gray-800">Email</span>
				<input
					class="mt-2 form-input block w-full shadow pointer-events-none"
					type="text"
					:value="email"
					disabled
				/>
			</label>
			<label class="mt-4 block">
				<span class="text-gray-800">Password</span>
				<input
					class="mt-2 form-input block w-full shadow"
					type="password"
					v-model="password"
					required
				/>
			</label>
			<div
				class="mt-6 text-red-600 whitespace-pre-line text-sm"
				v-if="errorMessage"
			>
				{{ errorMessage }}
			</div>
			<Button class="mt-6" type="primary" :disabled="!password">
				Submit
			</Button>
		</form>
	</LoginBox>
	<div class="text-center mt-20 px-6" v-else-if="!fetching && !email">
		Account Key <strong>{{ requestKey }}</strong> is invalid or expired.
	</div>
</template>

<script>
import LoginBox from './partials/LoginBox';

export default {
	name: 'ResetPassword',
	components: {
		LoginBox
	},
	props: ['requestKey'],
	data() {
		return {
			fetching: false,
			email: null,
			password: null,
			errorMessage: null
		};
	},
	async mounted() {
		this.fetching = true;
		try {
			let res = await this.$call(
				'press.api.account.get_user_for_reset_password_key',
				{
					key: this.requestKey
				}
			);
			this.email = res || null;
		} finally {
			this.fetching = false;
		}
	},
	methods: {
		async resetPassword() {
			try {
				this.errorMessage = null;
				await this.$call('press.api.account.reset_password', {
					key: this.requestKey,
					password: this.password
				});
				window.location.reload();
			} catch (error) {
				this.errorMessage = error.messages.join('\n').replace(/<br>/gi, '\n');
			}
		}
	}
};
</script>
