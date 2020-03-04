<template>
	<LoginBox v-if="!fetching && email">
		<div class="mb-8">
			<span class="text-lg">Set a password for your account</span>
		</div>
		<form class="flex flex-col" @submit.prevent="setupAccount">
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
				/>
			</label>
			<div
				class="mt-6 text-red-600 whitespace-pre-line text-sm"
				v-if="errorMessage"
			>
				{{ errorMessage }}
			</div>
			<Button
				class="mt-6 bg-brand focus:bg-blue-600 hover:bg-blue-400 text-white shadow"
				:disabled="!password"
				type="submit"
			>
				Submit
			</Button>
		</form>
	</LoginBox>
	<div class="text-center mt-20 px-6" v-else-if="!fetching && !email">
		Account Key <strong>{{ accountKey }}</strong> is invalid or expired.
		<a class="text-brand font-medium" href="#/signup">Sign up</a>
		for a new account.
	</div>
	<div v-else></div>
</template>

<script>
import LoginBox from './partials/LoginBox';

export default {
	name: 'SetupAccount',
	components: {
		LoginBox
	},
	props: ['accountKey'],
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
			let res = await this.$call('press.api.account.get_user_for_key', {
				key: this.accountKey
			});
			this.email = res || null;
		} finally {
			this.fetching = false;
		}
	},
	methods: {
		async setupAccount() {
			try {
				this.errorMessage = null;
				await this.$call('press.api.account.setup_account', {
					key: this.accountKey,
					password: this.password
				});
				this.$router.push('/sites');
				window.location.reload();
			} catch (error) {
				this.errorMessage = error.messages.join('\n').replace(/<br>/gi, '\n');
			}
		}
	}
};
</script>
