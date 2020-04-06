<template>
	<LoginBox v-if="!successMessage">
		<div class="mb-8">
			<span v-if="!forgot" class="text-lg">
				Log in to your account
			</span>
			<span v-else class="text-lg">Reset your password</span>
		</div>
		<form class="flex flex-col" @submit.prevent="login">
			<label class="block">
				<span class="text-gray-800">Email</span>
				<input
					class="block w-full mt-2 shadow form-input"
					placeholder="johndoe@mail.com"
					v-model="email"
					:type="email !== 'Administrator' ? 'email' : ''"
					required
				/>
			</label>
			<label class="block mt-4" v-if="!forgot">
				<span class="text-gray-800">Password</span>
				<div class="relative">
					<input
						class="block w-full mt-2 shadow form-input"
						type="password"
						placeholder="******"
						v-model="password"
						required
					/>
					<router-link
						to="/login/forgot"
						class="absolute inset-y-0 right-0 flex items-center pr-3 text-sm text-gray-900 underline"
					>
						Forgot?
					</router-link>
				</div>
			</label>
			<ErrorMessage v-if="errorMessage" class="mt-6">
				{{ errorMessage }}
			</ErrorMessage>
			<router-link
				v-if="forgot"
				to="/login"
				class="block mt-2 text-sm text-left"
			>
				I remember my password
			</router-link>
			<Button
				class="mt-6"
				:disabled="state === 'RequestStarted'"
				@click="loginOrResetPassword"
				type="primary"
			>
				Submit
			</Button>
			<template v-if="!forgot">
				<div class="mt-10 text-center border-t">
					<div class="transform -translate-y-1/2">
						<span
							class="px-2 text-xs leading-8 tracking-wider text-gray-800 uppercase bg-white"
						>
							Or
						</span>
					</div>
				</div>
				<router-link class="text-sm text-center" to="/signup">
					Sign up for a new account
				</router-link>
			</template>
		</form>
	</LoginBox>
	<div class="px-6 mt-20 text-center" v-else>
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
			successMessage: null
		};
	},
	watch: {
		forgot() {
			this.errorMessage = null;
			this.state = null;
			this.password = null;
			this.successMessage = null;
		}
	},
	methods: {
		async loginOrResetPassword() {
			try {
				this.errorMessage = null;
				this.state = 'RequestStarted';
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
