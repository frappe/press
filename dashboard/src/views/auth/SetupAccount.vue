<template>
	<LoginBox
		v-if="!$resources.validateRequestKey.loading && email"
		:title="
			!isInvitation
				? 'Set up your account'
				: `Invitation to join team: ${invitationToTeam}`
		"
	>
		<form
			class="flex flex-col"
			@submit.prevent="$resources.setupAccount.submit()"
		>
			<div class="space-y-4">
				<Input
					v-if="oauthSignup == 0"
					label="Email"
					input-class="pointer-events-none"
					type="text"
					:modelValue="email"
					autocomplete="off"
					disabled
				/>
				<template v-if="oauthSignup == 0">
					<Input
						label="First Name"
						type="text"
						v-model="firstName"
						name="fname"
						autocomplete="given-name"
						required
					/>
					<Input
						label="Last Name"
						type="text"
						v-model="lastName"
						name="lname"
						autocomplete="family-name"
						required
					/>
					<Input
						label="Password"
						type="password"
						v-model="password"
						name="password"
						autocomplete="new-password"
						required
					/>
				</template>
				<Input
					type="select"
					:options="countries"
					v-if="!isInvitation"
					label="Country"
					v-model="country"
					:value="country"
					required
				/>
				<div class="mt-4 flex">
					<input
						type="checkbox"
						v-model="termsAccepted"
						class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
						required
					/>
					<label class="ml-1 text-sm text-gray-900">
						By clicking on <span v-if="!isInvitation">Submit</span
						><span v-else>Accept</span>, you accept our
						<a href="https://frappecloud.com/terms" class="text-blue-600"
							>Terms of Service</a
						>,
						<a href="https://frappecloud.com/privacy" class="text-blue-600"
							>Privacy Policy</a
						>
						&#38;
						<a
							href="https://frappecloud.com/cookie-policy"
							class="text-blue-600"
							>Cookie Policy</a
						>
					</label>
				</div>
			</div>
			<ErrorMessage class="mt-4" :message="$resourceErrors" />
			<Button
				class="mt-4"
				appearance="primary"
				:loading="$resources.setupAccount.loading"
			>
				<span v-if="!isInvitation"> Submit </span>
				<span v-else> Accept </span>
			</Button>
		</form>
	</LoginBox>
	<div
		class="mt-20 px-6 text-center"
		v-else-if="!$resources.validateRequestKey.loading && !email"
	>
		Account Key <strong>{{ requestKey }}</strong> is invalid or expired.
		<Link to="/signup">Sign up</Link>
		for a new account.
	</div>
	<div v-else></div>
</template>

<script>
import LoginBox from '@/views/partials/LoginBox.vue';

export default {
	name: 'SetupAccount',
	components: {
		LoginBox
	},
	props: ['requestKey', 'joinRequest'],
	data() {
		return {
			email: null,
			firstName: null,
			lastName: null,
			password: null,
			errorMessage: null,
			userExists: null,
			invitationToTeam: null,
			isInvitation: null,
			oauthSignup: 0,
			country: null,
			termsAccepted: false,
			invitedByParentTeam: false,
			countries: []
		};
	},
	resources: {
		validateRequestKey() {
			return {
				method: 'press.api.account.get_email_from_request_key',
				params: {
					key: this.requestKey
				},
				auto: true,
				onSuccess(res) {
					if (res && res.email) {
						this.email = res.email;
						this.firstName = res.first_name;
						this.lastName = res.last_name;
						this.country = res.country;
						this.userExists = res.user_exists;
						this.invitationToTeam = res.team;
						this.isInvitation = res.is_invitation;
						this.invitedByParentTeam = res.invited_by_parent_team;
						this.oauthSignup = res.oauth_signup;
						this.countries = res.countries;
					}
				}
			};
		},
		setupAccount() {
			return {
				method: 'press.api.account.setup_account',
				params: {
					key: this.requestKey,
					password: this.password,
					first_name: this.firstName,
					last_name: this.lastName,
					country: this.country,
					is_invitation: this.isInvitation,
					user_exists: this.userExists,
					invited_by_parent_team: this.invitedByParentTeam,
					accepted_user_terms: this.termsAccepted,
					oauth_signup: this.oauthSignup
				},
				onSuccess(res) {
					//window.posthog.capture('completed_client_fc_setup_account');
					if (res) {
						this.$router.push(res.dashboard_route || '/');
					}
					window.location.reload();
				}
			};
		}
	},
	methods: {
		showFormFields() {
			let show = true;
			show = !this.userExists;
			show = this.oauthSignup == 0;
			return show;
		}
	}
};
</script>
