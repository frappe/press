<template>
	<LoginBox v-if="state != 'Signup Success'">
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
					v-model="email"
					required
				/>
			</label>
			<div
				class="mt-6 text-sm text-red-600 whitespace-pre-line"
				v-if="errorMessage"
			>
				{{ errorMessage }}
			<Button class="mt-6" :disabled="state === 'Signing Up'" type="primary">
				Signup
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
				Already have an account? Login
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
			state: 'Idle', // Idle, Signing Up, Signup Error, Signup Success
			email: null,
			errorMessage: null
		};
	},
	methods: {
		async signup() {
			try {
				this.errorMessage = null;
				this.state = 'Signing Up';
				await this.$call('press.api.account.signup', {
					email: this.email
				});
				this.state = 'Signup Success';
			} catch (error) {
				this.errorMessage = error.messages.join('\n');
				this.state = 'Signup Error';
			}
		}
	}
};
</script>
