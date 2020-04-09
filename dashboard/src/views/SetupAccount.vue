<template>
	<LoginBox v-if="!fetching && email">
		<div class="mb-8">
			<span v-if="!isInvitation" class="text-lg">
				Set up your account
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
					autocomplete="off"
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
						name="fname"
						autocomplete="given-name"
						required
					/>
				</label>
				<label class="block mt-4">
					<span class="text-gray-800">Last Name</span>
					<input
						class="block w-full mt-2 shadow pointer-events-none form-input"
						type="text"
						v-model="lastName"
						name="lname"
						autocomplete="family-name"
						required
					/>
				</label>
				<label class="block mt-4">
					<span class="text-gray-800">Password</span>
					<input
						class="block w-full mt-2 shadow form-input"
						type="password"
						v-model="password"
						name="password"
						autocomplete="new-password"
					/>
				</label>
			</template>
			<label class="block mt-4" v-if="!isInvitation">
				<span class="text-gray-800">Country</span>
				<select class="block w-full mt-2 shadow form-select" v-model="country">
					<option v-for="country in countries" :key="country">
						{{ country }}
					</option>
				</select>
			</label>
			<ErrorMessage class="mt-6 " v-if="errorMessage">
				{{ errorMessage }}
			</ErrorMessage>
			<Button class="mt-6" type="primary" :disabled="disableButton">
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
			state: null,
			fetching: false,
			countries: [],
			email: null,
			firstName: null,
			lastName: null,
			password: null,
			errorMessage: null,
			userExists: null,
			invitationToTeam: null,
			isInvitation: null,
			country: null
		};
	},
	mounted() {
		this.getEmailFromRequestKey();
		this.fetchCountryList();
	},
	methods: {
		async getEmailFromRequestKey() {
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
					this.country = res.country;
					this.userExists = res.user_exists;
					this.invitationToTeam = res.team;
					this.isInvitation = res.is_invitation;
				}
			} finally {
				this.fetching = false;
			}
		},
		async setupAccount() {
			try {
				this.errorMessage = null;
				await this.$call('press.api.account.setup_account', {
					key: this.requestKey,
					password: this.password,
					first_name: this.firstName,
					last_name: this.lastName,
					country: this.country,
					is_invitation: this.isInvitation
				});
				this.$router.push('/sites');
				window.location.reload();
			} catch (error) {
				this.errorMessage = error.messages.join('\n').replace(/<br>/gi, '\n');
			}
		},
		async fetchCountryList() {
			this.countries = await this.$call('press.api.account.country_list');
		}
	},
	computed: {
		disableButton() {
			if (this.state == 'RequestStarted') {
				return true;
			}
			if (this.userExists) {
				return !this.country;
			}
			if (this.isInvitation) {
				return !(this.password && this.firstName && this.lastName);
			} else {
				return !(
					this.password &&
					this.firstName &&
					this.lastName &&
					this.country
				);
			}
		}
	}
};
</script>
