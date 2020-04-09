<template>
	<LoginBox v-if="!fetching && email">
		<div class="mb-8">
			<span class="text-lg">Set a new password for your account</span>
		</div>
		<form class="flex flex-col" @submit.prevent="resetPassword">
			<label class="block">
				<span class="text-gray-800">Email</span>
				<input
					class="block w-full mt-2 shadow pointer-events-none form-input"
					type="text"
					:value="email"
					name="email"
					autocomplete="off"
					disabled
				/>
			</label>
			<label class="block mt-4">
				<span class="text-gray-800">Password</span>
				<input
					class="block w-full mt-2 shadow form-input"
					type="password"
					v-model="password"
					name="password"
					autocomplete="new-password"
					required
				/>
			</label>
			<ErrorMessage class="mt-6" v-if="errorMessage">
				{{ errorMessage }}
			</ErrorMessage>
			<Button
				class="mt-6"
				type="primary"
				:disabled="!password || state === 'RequestStarted'"
			>
				Submit
			</Button>
		</form>
	</LoginBox>
	<div class="px-6 mt-20 text-center" v-else-if="!fetching && !email">
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
			state: null,
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
			await this.$call('press.api.account.reset_password', {
				key: this.requestKey,
				password: this.password
			});
			window.location.reload();
		}
	}
};
</script>
