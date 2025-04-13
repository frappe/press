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
					{{
						invitedBy
							? 'Invitation to join'
							: 'Set up your Frappe Cloud account'
					}}
				</div>
				<div class="mt-2 text-center text-sm text-gray-600" v-if="invitedBy">
					Invitation by {{ invitedBy }}
				</div>
				<form class="mt-6 flex flex-col" @submit.prevent="submitForm">
					<template v-if="is2FA">
						<FormControl
							label="2FA Code from your Authenticator App"
							placeholder="123456"
							v-model="twoFactorCode"
							required
						/>
						<Button
							class="mt-4"
							:loading="$resources.verify2FA.loading"
							variant="solid"
							@click="
								$resources.verify2FA.submit({
									user: email,
									totp_code: twoFactorCode,
								})
							"
						>
							Verify
						</Button>
						<ErrorMessage class="mt-2" :message="$resources.verify2FA.error" />
					</template>
					<template v-else>
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
									<Link
										class="!text-gray-700"
										href="https://frappecloud.com/policies"
										target="_blank"
									>
										Terms and Policies
									</Link>
								</label>
							</div>
						</div>
						<ErrorMessage
							class="mt-4"
							:message="$resources.setupAccount.error"
						/>
						<Button
							class="mt-6"
							variant="solid"
							:loading="$resources.setupAccount.loading"
						>
							{{
								is2FA ? 'Verify' : isInvitation ? 'Accept' : 'Create account'
							}}
						</Button>
					</template>
				</form>
				<template #footer v-if="saasProduct">
					<div
						class="mt-2 flex w-full items-center justify-center text-sm text-gray-600"
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
			errorMessage: null,
			userExists: null,
			twoFactorCode: null,
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
				onSuccess() {
					let path = '/dashboard/create-site/app-selector';
					if (this.saasProduct) {
						path = `/dashboard/create-site/${this.saasProduct.name}/setup`;
					}
					window.location.href = path;
				},
			};
		},
		is2FAEnabled() {
			return {
				url: 'press.api.account.is_2fa_enabled',
			};
		},
		verify2FA() {
			return {
				url: 'press.api.account.verify_2fa',
				onSuccess() {
					this.$resources.setupAccount.submit();
				},
			};
		},
	},
	computed: {
		is2FA() {
			return (
				this.$route.name === 'Setup Account' && this.$route.query.two_factor
			);
		},
	},
	methods: {
		submitForm() {
			if (this.invitedBy) {
				this.$resources.is2FAEnabled.submit(
					{
						user: this.email,
					},
					{
						onSuccess: (two_factor_enabled) => {
							if (two_factor_enabled) {
								this.$router.push({
									name: 'Setup Account',
									query: {
										...this.$route.query,
										two_factor: 1,
									},
								});
							} else {
								this.$resources.setupAccount.submit();
							}
						},
					},
				);
			} else {
				this.$resources.setupAccount.submit();
			}
		},
	},
};
</script>
