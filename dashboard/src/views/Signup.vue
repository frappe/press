<template>
	<LoginBox v-if="state !== 'SignupSuccess'">
		<div class="mb-8">
			<span class="text-lg">Create your account</span>
		</div>
		<form class="flex flex-col" @submit.prevent="signup">
			<label class="block">
				<span class="text-gray-800">Email</span>
				<input
					class="block w-full mt-2 shadow form-input"
					type="email"
					placeholder="johndoe@mail.com"
					autocomplete="email"
					v-model="email"
					required
				/>
			</label>
			<ErrorMessage class="mt-6" v-if="errorMessage">
				{{ errorMessage }}
			</ErrorMessage>
			<Button
				class="mt-6"
				:disabled="state === 'RequestStarted'"
				type="primary"
			>
				Submit
			</Button>
			<div class="mt-10 text-center border-t">
				<div class="transform -translate-y-1/2">
					<span
						class="px-2 text-xs leading-8 tracking-wider text-gray-800 uppercase bg-white"
					>
						Or
					</span>
				</div>
			</div>
			<router-link class="text-sm text-center" to="/login">
				Already have an account? Log in.
			</router-link>
		</form>
	</LoginBox>
	<div class="px-6 mt-20 text-center" v-else>
		We have sent an email to
		<span class="font-semibold">{{ email }}</span
		>. Please click on the link received to verify your email and set up your
		account.
	</div>
</template>

<script>
import LoginBox from './partials/LoginBox';

export default {
	name: 'Signup',
	components: {
		LoginBox
	},
	data() {
		return {
			state: null,
			email: null,
			errorMessage: null
		};
	},
	methods: {
		async signup() {
			await this.$call('press.api.account.signup', {
				email: this.email
			});
			this.state = 'SignupSuccess';
		}
	}
};
</script>
