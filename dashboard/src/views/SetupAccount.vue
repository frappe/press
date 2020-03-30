<template>
	<LoginBox v-if="!fetching && email">
		<div class="mb-8">
			<span v-if="!isInvitation" class="text-lg">
				Setup your account
			</span>
			<span v-else class="text-lg"
				>Invitation to join team <strong>{{ invitationToTeam }}</strong></span
			>
		</div>
		<form class="flex flex-col" @submit.prevent="setupAccount">
			<label class="block">
				<span class="text-gray-800">Email</span>
				<input
					class="block w-full mt-2 shadow pointer-events-none form-input"
					type="text"
					:value="email"
					disabled
				/>
			</label>
			<template v-if="!userExists">
				<label class="block mt-4">
					<span class="text-gray-800">First Name</span>
					<input
						class="block w-full mt-2 shadow pointer-events-none form-input"
						type="text"
						v-model="firstName"
						required
					/>
				</label>
				<label class="block mt-4">
					<span class="text-gray-800">Last Name</span>
					<input
						class="block w-full mt-2 shadow pointer-events-none form-input"
						type="text"
						v-model="lastName"
						required
					/>
				</label>
				<label class="block mt-4">
					<span class="text-gray-800">Password</span>
					<input
						class="block w-full mt-2 shadow form-input"
						type="password"
						v-model="password"
					/>
				</label>
			</template>
			<div
				class="mt-6 text-sm text-red-600 whitespace-pre-line"
				v-if="errorMessage"
			>
				{{ errorMessage }}
			</div>
			<Button
				class="mt-6 text-white bg-blue-500 shadow focus:bg-blue-600 hover:bg-blue-400"
				:disabled="!(password && firstName && lastName) && !userExists"
				type="submit"
			>
				<span v-if="!isInvitation">
					Submit
				</span>
				<span v-else>
					Accept
				</span>
			</Button>
		</form>
	</LoginBox>
	<div class="px-6 mt-20 text-center" v-else-if="!fetching && !email">
		Account Key <strong>{{ requestKey }}</strong> is invalid or expired.
		<a class="font-medium text-brand" href="#/signup">Sign up</a>
		for a new account.
	</div>
	<div v-else></div>
</template>

<script>
import LoginBox from './partials/LoginBox';

export default {
	name: 'SetupAccount',
	components: {
		LoginBox
	},
	props: ['requestKey', 'joinRequest'],
	data() {
		return {
			fetching: false,
			email: null,
			firstName: null,
			lastName: null,
			password: null,
			errorMessage: null,
			userExists: null,
			invitationToTeam: null,
			isInvitation: null
		};
	},
	async mounted() {
		this.fetching = true;
		try {
			let res = await this.$call(
				'press.api.account.get_email_from_request_key',
				{
					key: this.requestKey
				}
			);
			if (res.email) {
				this.email = res.email;
				this.userExists = res.user_exists;
				this.invitationToTeam = res.team;
				this.isInvitation = res.is_invitation;
			}
		} finally {
			this.fetching = false;
		}
	},
	methods: {
		async setupAccount() {
			try {
				this.errorMessage = null;
				await this.$call('press.api.account.setup_account', {
					key: this.requestKey,
					password: this.password,
					first_name: this.firstName,
					last_name: this.lastName,
					is_invitation: this.isInvitation
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
