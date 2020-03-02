<template>
	<div class="h-full bg-gray-100 pt-16">
		<div v-if="state != 'Signup Success'">
			<div class="flex">
				<h1 class="mx-auto font-bold text-2xl px-6 py-4">Frappe Cloud</h1>
			</div>
			<div class="mt-6 mx-auto w-112 py-12 px-12 rounded-md bg-white shadow-lg">
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
						/>
					</label>
					<label class="mt-4 block">
						<span class="text-gray-800">Last Name</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="text"
							placeholder="Doe"
							v-model="lastName"
						/>
					</label>
					<label class="mt-4 block">
						<span class="text-gray-800">Email</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="email"
							placeholder="johndoe@mail.com"
							v-model="email"
						/>
					</label>
					<div class="mt-6 text-red-600 whitespace-pre-line text-sm" v-if="errorMessage">
						{{ errorMessage }}
					</div>
					<Button
						class="mt-6 bg-brand focus:bg-blue-600 hover:bg-blue-400 text-white shadow"
						:disabled="state === 'Signing Up'"
					>
						Signup
					</Button>
					<div class="mt-10 text-center border-t">
						<div class="transform -translate-y-1/2">
							<span class="bg-white px-2 leading-8 text-xs text-gray-800 uppercase tracking-wider">
								Or
							</span>
						</div>
					</div>
					<router-link class="text-center text-sm" to="/login">
						Already have an account? Login
					</router-link>
				</form>
			</div>
		</div>
		<div class="text-center mt-20" v-else>
			We have sent an email to <span class="font-semibold">{{ email }}</span
			>. Please click on the link received to verify your email and set up your
			account.
		</div>
	</div>
</template>

<script>
export default {
	name: 'Signup',
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
