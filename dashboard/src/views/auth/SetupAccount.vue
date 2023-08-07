<template>
	<LoginBox
		v-if="!$resources.validateRequestKey.loading && email"
		:title="
			!isInvitation
				? 'Set up your account'
				: `Invitation to join team: ${invitationToTeam}`
		"
	>
		<template #logo v-if="saasProduct">
			<div class="mx-auto flex flex-col items-center">
				<img
					class="mb-1"
					v-if="saasProduct.logo"
					:src="saasProduct.logo"
					:alt="saasProduct.title"
				/>
				<div class="text-4xl font-semibold text-gray-900" v-else>
					{{ saasProduct.title }}
				</div>
				<div class="text-base text-gray-700">Powered by Frappe Cloud</div>
			</div>
		</template>
		<form
			class="flex flex-col"
			@submit.prevent="$resources.setupAccount.submit()"
		>
			<div class="space-y-4">
				<FormControl
					v-if="oauthSignup == 0"
					label="Email"
					type="text"
					:modelValue="email"
					disabled
				/>
				<template v-if="oauthSignup == 0">
					<FormControl
						label="First Name"
						type="text"
						v-model="firstName"
						name="fname"
						autocomplete="given-name"
						required
					/>
					<FormControl
						label="Last Name"
						type="text"
						v-model="lastName"
						name="lname"
						autocomplete="family-name"
						required
					/>
					<FormControl
						label="Password"
						type="password"
						v-model="password"
						name="password"
						autocomplete="new-password"
						required
					/>
				</template>
				<FormControl
					type="select"
					:options="countries"
					v-if="!isInvitation"
					label="Country"
					v-model="country"
					required
				/>
				<div class="mt-4 flex items-start">
					<label class="text-base text-gray-900">
						<FormControl type="checkbox" v-model="termsAccepted" />
						By clicking on
						<span>{{ isInvitation ? 'Accept' : 'Submit' }}</span
						>, you accept our
						<Link href="https://frappecloud.com/terms" target="_blank"
							>Terms of Service </Link
						>,
						<Link href="https://frappecloud.com/privacy" target="_blank">
							Privacy Policy
						</Link>
						&#38;
						<Link href="https://frappecloud.com/cookie-policy" target="_blank">
							Cookie Policy
						</Link>
					</label>
				</div>
			</div>
			<ErrorMessage class="mt-4" :message="$resourceErrors" />
			<Button
				class="mt-4"
				variant="solid"
				:loading="$resources.setupAccount.loading"
			>
				{{ isInvitation ? 'Accept' : 'Create account' }}
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
import { FormControl } from 'frappe-ui';
import Link from '@/components/Link.vue';

export default {
	name: 'SetupAccount',
	components: {
		LoginBox,
		FormControl,
		Link
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
			countries: [],
			saasProduct: null
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
						this.saasProduct = res.saas_product;
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
