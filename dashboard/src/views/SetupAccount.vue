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
					label="Email"
					input-class="pointer-events-none"
					type="text"
					:modelValue="email"
					autocomplete="off"
					disabled
				/>
				<template v-if="!userExists">
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
					type="text"
					v-if="!isInvitation"
					label="Country"
					v-model="country"
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
			<ErrorMessage class="mt-4" :error="$resourceErrors" />
			<Button
				class="mt-4"
				type="primary"
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
import LoginBox from './partials/LoginBox.vue';

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
			country: null,
			termsAccepted: false
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
						this.country = res.country;
						this.userExists = res.user_exists;
						this.invitationToTeam = res.team;
						this.isInvitation = res.is_invitation;
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
					accepted_user_terms: this.termsAccepted
				},
				onSuccess(res) {
					if (res) {
						this.$router.push(res.dashboard_route || '/');
					}
					window.location.reload();
				}
			};
		}
	}
};
</script>
