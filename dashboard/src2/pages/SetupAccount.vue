<template>
	<div
		class="flex h-screen overflow-hidden bg-gray-50"
		v-if="!$resources.validateRequestKey.loading && email"
	>
		<div class="w-full overflow-auto">
			<LoginBox>
				<template v-slot:logo v-if="saasProduct">
					<div class="mx-auto flex items-center space-x-2">
						<img
							class="inline-block h-7 w-7 rounded-sm"
							:src="saasProduct?.logo"
						/>
						<span
							class="select-none text-xl font-semibold tracking-tight text-gray-900"
						>
							{{ saasProduct?.title }}
						</span>
					</div>
				</template>
				<div
					class="text-center text-lg font-medium leading-5 tracking-tight text-gray-900"
				>
					{{ invitedBy ? 'Invitation to join' : 'Set up your account' }}
				</div>
				<div class="mt-2 text-center text-sm text-gray-600" v-if="invitedBy">
					Invitation by {{ invitedBy }}
				</div>
				<form
					class="mt-6 flex flex-col"
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
						<template v-if="oauthSignup == 0 && !userExists">
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
								v-if="!oauthDomain"
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
						<div class="!mt-6 flex gap-2">
							<FormControl type="checkbox" v-model="termsAccepted" />
							<label class="text-base text-gray-700">
								I accept the
								<Link href="https://frappecloud.com/policies" target="_blank">
									Terms and Policies
								</Link>
							</label>
						</div>
					</div>
					<ErrorMessage class="mt-4" :message="$resources.setupAccount.error" />
					<Button
						class="mt-4"
						variant="solid"
						:loading="$resources.setupAccount.loading"
					>
						{{ isInvitation ? 'Accept' : 'Create account' }}
					</Button>
				</form>
				<template #footer v-if="saasProduct">
					<div
						class="mt-2 flex w-full items-center justify-center text-sm text-gray-700"
					>
						Powered by Frappe Cloud
					</div>
				</template>
			</LoginBox>
		</div>
	</div>
	<div
		class="mt-20 px-6 text-center"
		v-else-if="!$resources.validateRequestKey.loading && !email"
	>
		Verification link is invalid or expired.
		<Link to="/signup">Sign up</Link>
		for a new account.
	</div>
	<div v-else></div>
</template>

<script>
import LoginBox from '../components/auth/LoginBox.vue';
import Link from '@/components/Link.vue';
import Form from '@/components/Form.vue';

export default {
	name: 'SetupAccount',
	components: {
		LoginBox,
		Link,
		Form,
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
			oauthDomain: false,
			country: null,
			termsAccepted: false,
			invitedBy: null,
			invitedByParentTeam: false,
			countries: [],
			saasProduct: null,
			signupValues: {},
		};
	},
	resources: {
		validateRequestKey() {
			return {
				url: 'press.api.account.validate_request_key',
				params: {
					key: this.requestKey,
					timezone: window.Intl
						? Intl.DateTimeFormat().resolvedOptions().timeZone
						: null,
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
						this.invitedBy = res.invited_by;
						this.isInvitation = res.is_invitation;
						this.invitedByParentTeam = res.invited_by_parent_team;
						this.oauthSignup = res.oauth_signup;
						this.oauthDomain = res.oauth_domain;
						this.countries = res.countries;
						this.saasProduct = res.product_trial;
					}
				},
			};
		},
		setupAccount() {
			return {
				url: 'press.api.account.setup_account',
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
					oauth_signup: this.oauthSignup,
					oauth_domain: this.oauthDomain,
				},
				onSuccess(account_request) {
					let path = '/dashboard/create-site/app-selector';
					if (this.saasProduct) {
						path = `/dashboard/create-site/${this.saasProduct.name}/setup?account_request=${account_request}`;
					}
					window.location.href = path;
				},
			};
		},
	},
};
</script>
