<template>
	<div class="h-full bg-gray-100 pt-16">
		<div v-if="!successMessage">
			<div class="flex">
				<h1 class="mx-auto font-bold text-2xl px-6 py-4">Frappe Cloud</h1>
			</div>
			<div class="mt-6 mx-auto w-112 py-12 px-12 rounded-md bg-white shadow-lg">
				<div class="mb-8">
					<span v-if="view === 'Login'" class="text-lg">
						Login to your account
					</span>
					<span v-else class="text-lg">Reset your password</span>
				</div>
				<form class="flex flex-col" @submit.prevent="login">
					<label class="block">
						<span class="text-gray-800">Email</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="email"
							placeholder="johndoe@mail.com"
							v-model="email"
							autofocus
						/>
					</label>
					<label class="mt-4 block" v-if="view === 'Login'">
						<span class="text-gray-800">Password</span>
						<div class="relative">
							<input
								class="mt-2 form-input block w-full shadow"
								type="password"
								placeholder="******"
								v-model="password"
							/>
							<button
								@click="view = 'Reset Password'"
								class="absolute flex items-center inset-y-0 right-0 pr-3 text-sm text-gray-900 underline"
							>
								Forgot?
							</button>
						</div>
					</label>
					<div
						class="mt-6 text-red-600 whitespace-pre-line text-sm"
						v-if="errorMessage"
					>
						{{ errorMessage }}
					</div>
					<Button
						class="mt-6 bg-brand focus:bg-blue-600 hover:bg-blue-400 text-white shadow"
						:disabled="state === 'Working'"
						@click="loginOrResetPassword"
					>
						{{ view }}
					</Button>
					<template v-if="view === 'Login'">
						<div class="mt-10 text-center border-t">
							<div class="transform -translate-y-1/2">
								<span
									class="bg-white px-2 leading-8 text-xs text-gray-800 uppercase tracking-wider"
								>
									Or
								</span>
							</div>
						</div>
						<router-link class="text-center text-sm" to="/signup">
							Signup for a new account
						</router-link>
					</template>
				</form>
			</div>
		</div>
		<div class="text-center mt-20" v-else>
			We have sent an email to <span class="font-semibold">{{ email }}</span
			>. Please click on the link received to reset your password.
		</div>
	</div>
</template>
<script>
export default {
	name: 'Login',
	data() {
		return {
			state: null, // Idle, Logging In, Login Error
			email: null,
			password: null,
			errorMessage: null,
			view: 'Login', // 'Reset Password'
			successMessage: null
		};
	},
	methods: {
		async loginOrResetPassword() {
			try {
				this.errorMessage = null;
				this.state = 'Working';
				if (this.view === 'Login') {
					await this.login();
				} else {
					await this.resetPassword();
				}
			} catch (error) {
				this.errorMessage = error.messages.join('\n');
			} finally {
				this.state = null;
			}
		},
		async login() {
			if (this.email && this.password) {
				await this.$store.auth.login(this.email, this.password);
				this.$router.push('/sites');
			}
		},
		async resetPassword() {
            await this.$store.auth.resetPassword(this.email);
			this.successMessage = true;
		}
	}
};
</script>
