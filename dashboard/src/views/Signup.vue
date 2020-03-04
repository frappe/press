<template>
	<LoginBox v-if="state != 'Signup Success'">
		<div class="mb-8">
			<span class="text-lg">Signup to create your account</span>
		</div>
		<form class="flex flex-col" @submit.prevent="signup">
			<label class="block">
				<span class="text-gray-800">First Name</span>
				<input
					class="mt-2 form-input block w-full shadow"
					type="text"
					placeholder="John"
					v-model="firstName"
					required
				/>
			</label>
			<label class="mt-4 block">
				<span class="text-gray-800">Last Name</span>
				<input
					class="mt-2 form-input block w-full shadow"
					type="text"
					placeholder="Doe"
					v-model="lastName"
					required
				/>
			</label>
			<label class="mt-4 block">
				<span class="text-gray-800">Email</span>
				<input
					class="mt-2 form-input block w-full shadow"
					type="email"
					placeholder="johndoe@mail.com"
					v-model="email"
					required
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
				:disabled="state === 'Signing Up'"
				type="submit"
			>
				Signup
			</Button>
			<div class="mt-10 text-center border-t">
				<div class="transform -translate-y-1/2">
					<span
						class="bg-white px-2 leading-8 text-xs text-gray-800 uppercase tracking-wider"
					>
						Or
					</span>
				</div>
			</div>
			<router-link class="text-center text-sm" to="/login">
				Already have an account? Login
			</router-link>
		</form>
	</LoginBox>
	<div class="text-center mt-20 px-6" v-else>
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
			firstName: null,
			lastName: null,
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
					first_name: this.firstName,
					last_name: this.lastName,
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
