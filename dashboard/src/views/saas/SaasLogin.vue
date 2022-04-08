<template>
	<LoginBox
		v-if="!successMessage"
		:title="!forgot ? 'Log in to your SaaS account' : 'Reset your password'"
	>
		<form class="flex flex-col" @submit.prevent="login">
			<Input
				label="Email"
				placeholder="johndoe@mail.com"
				v-model="email"
				name="email"
				autocomplete="email"
				:type="email !== 'Administrator' ? 'email' : 'text'"
				required
			/>
			<Input
				class="mt-4"
				v-if="!forgot"
				label="Password"
				type="password"
				placeholder="•••••"
				v-model="password"
				name="password"
				autocomplete="current-password"
				required
			/>
			<div class="mt-2 text-sm">
				<router-link v-if="forgot" to="/login">
					I remember my password
				</router-link>
				<router-link v-else to="/login/forgot"> Forgot Password </router-link>
			</div>
			<ErrorMessage :error="errorMessage" class="mt-4" />
			<Button
				class="mt-4"
				:disabled="state === 'RequestStarted'"
				@click="loginOrResetPassword"
				type="primary"
			>
				Submit
			</Button>
			<template v-if="!forgot">
				<div class="mt-10 border-t text-center">
					<div class="-translate-y-1/2 transform">
						<span
							class="bg-white px-2 text-xs uppercase leading-8 tracking-wider text-gray-800"
						>
							Or
						</span>
					</div>
				</div>
				<router-link class="text-center text-base" to="/signup">
					Sign up for a new account
				</router-link>
			</template>
		</form>
	</LoginBox>
	<SuccessCard v-else class="mx-auto mt-20" title="Password Reset Link Sent.">
		We have sent an email to <span class="font-semibold">{{ email }}</span
		>. Please click on the link received to reset your password.
	</SuccessCard>
</template>
<script>
import LoginBox from '../partials/LoginBox.vue';

export default {
	name: 'SaasLogin',
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
			successMessage: null,
			redirect_route: '/saas/upgrade'
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
	resources: {
		login() {
			return {
				method: 'login',
				params: {
					usr: this.email,
					pwd: this.password
				},
				onSuccess(res) {
					if (res) {
						this.$account.fetchAccount();
						this.$auth.isLoggedIn = true;
						return res;
					}
				}
			};
		}
	},
	async mounted() {
		if (this.$route?.query?.route) {
			this.redirect_route = this.$route.query.route;
			this.$router.replace({ query: null });
		}
		localStorage.removeItem('was_saas_logout');
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
				let res = await this.$auth.login(this.email, this.password);
				if (res) {
					this.$saas.loginToSaas(true, null, null); // fetch this randomly from active subs
					this.$router.push(this.redirect_route || res.dashboard_route || '/');
				}
			}
		},
		async resetPassword() {
			await this.$auth.resetPassword(this.email);
			this.successMessage = true;
		}
	}
};
</script>
