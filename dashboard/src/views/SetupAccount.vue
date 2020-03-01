<template>
	<div class="h-full bg-gray-100 pt-16" v-if="!fetching && email">
		<div class="flex">
			<h1 class="mx-auto font-bold text-2xl px-6 py-4">Frappe Cloud</h1>
		</div>
		<div class="mt-6 mx-auto w-112 py-12 px-12 rounded-md bg-white shadow-lg">
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
				<div class="mt-6 text-red-600 whitespace-pre-line text-sm" v-if="errorMessage">
					{{ errorMessage }}
				</div>
				<Button
					class="mt-6 bg-brand focus:bg-blue-600 hover:bg-blue-400 text-white shadow"
					:disabled="!password"
				>
					Submit
				</Button>
			</form>
		</div>
	</div>
	<div class="text-center mt-20" v-else-if="!fetching && !email">
		Account Key <strong>{{ accountKey }}</strong> is invalid or expired.
		<a class="text-brand font-medium" href="#/signup">
			Sign up
		</a>
		for a new account.
	</div>
</template>

<script>
export default {
	name: 'SetupAccount',
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
