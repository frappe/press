<template>
	<LoginBox v-if="!successMessage">
		<div class="mb-8">
			<span v-if="!forgot" class="text-lg">
				Login to your account
			</span>
			<span v-else class="text-lg">Reset your password</span>
		</div>
		<form class="flex flex-col" @submit.prevent="login">
			<label class="block">
				<span class="text-gray-800">Email</span>
				<input
					class="mt-2 form-input block w-full shadow"
					placeholder="johndoe@mail.com"
					v-model="email"
					:type="email !== 'Administrator' ? 'email' : ''"
					required
				/>
			</label>
			<label class="mt-4 block" v-if="!forgot">
				<span class="text-gray-800">Password</span>
				<div class="relative">
					<input
						class="mt-2 form-input block w-full shadow"
						type="password"
						placeholder="******"
						v-model="password"
						required
					/>
					<router-link
						to="/login/forgot"
						class="absolute flex items-center inset-y-0 right-0 pr-3 text-sm text-gray-900 underline"
					>
						Forgot?
					</router-link>
				</div>
			</label>
			<div
				class="mt-6 text-red-600 whitespace-pre-line text-sm"
				v-if="errorMessage"
			>
				{{ errorMessage }}
			</div>
			<router-link
				v-if="forgot"
				to="/login"
				class="mt-2 block text-left text-sm"
			>
				I remember my password
			</router-link>
			<Button
				class="mt-6 bg-blue-500 focus:bg-blue-600 hover:bg-blue-400 text-white shadow"
				:disabled="state === 'Working'"
				@click="loginOrResetPassword"
				type="submit"
			>
				{{ forgot ? 'Reset Password' : 'Login' }}
			</Button>
			<template v-if="!forgot">
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
	</LoginBox>
	<div class="text-center mt-20 px-6" v-else>
		We have sent an email to <span class="font-semibold">{{ email }}</span
		>. Please click on the link received to reset your password.
	</div>
</template>
<script>
import LoginBox from './partials/LoginBox';

export default {
	name: 'Login',
	props: {
		forgot: {
			default: false
		}
	},
	components: {
		LoginBox
	},
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
				if (!this.forgot) {
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
