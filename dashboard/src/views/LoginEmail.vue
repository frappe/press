<template>
	<div>
		<LoginBox v-if="!code" title="Log in to your account">
			<form class="flex flex-col" @submit.prevent>
				<Input
					label="Email"
					placeholder="johndoe@mail.com"
					v-model="email"
					name="email"
					autocomplete="email"
					:type="email !== 'Administrator' ? 'email' : 'text'"
					required
				/>
				<ErrorMessage
					:error="$resources.sendVerificationLink.error"
					class="mt-4"
				/>
				<Button
					class="mt-4"
					:loading="$resources.sendVerificationLink.loading"
					@click="$resources.sendVerificationLink.submit()"
					type="primary"
				>
					Submit
				</Button>
				<template>
					<div class="mt-10 text-center border-t">
						<div class="transform -translate-y-1/2">
							<span
								class="px-2 text-xs leading-8 tracking-wider text-gray-800 uppercase bg-white"
							>
								Or
							</span>
						</div>
					</div>
					<router-link class="text-base text-center" to="/signup">
						Sign up for a new account
					</router-link>
				</template>
			</form>
		</LoginBox>
		<SuccessCard
			v-else-if="code"
			class="mx-auto mt-20"
			title="Awaiting Confirmation"
		>
			<template v-if="!verified">
				<p class="my-2 font-semibold">
					Do not close this window until opening the email link.
				</p>
				<p>
					We just sent an email to
					<span class="font-semibold">{{ email }}</span>
				</p>
				<p>
					Verify that the code matches the following text:
				</p>
				<div
					class="inline-block px-3 py-2 mt-2 font-semibold bg-gray-100 rounded"
				>
					{{ code }}
				</div>
			</template>
			<div v-else>Logging you in...</div>
		</SuccessCard>
	</div>
</template>
<script>
import LoginBox from './partials/LoginBox.vue';

export default {
	name: 'Login',
	components: {
		LoginBox
	},
	data() {
		return {
			email: null,
			code: null,
			verified: false
		};
	},
	resources: {
		sendVerificationLink() {
			return {
				method: 'press.api.account.send_verification_link',
				params: {
					email: this.email
				},
				onSuccess(code) {
					if (code) {
						this.code = code;
						this.$socket.on(`user_login:${code}`, this.onVerification);
					}
				}
			};
		}
	},
	methods: {
		async onVerification() {
			this.verified = true;
			let result = await this.$call('press.api.account.login_via_email', {
				code: this.code
			});
			if (result == 'success') {
				await this.$account.fetchAccount();
				this.$auth.isLoggedIn = true;
				await this.$router.push('/sites');
			}
		}
	}
};
</script>
