<template>
	<div
		class="flex h-screen overflow-hidden"
		v-if="!$resources.validateRequestKey.loading && email"
	>
		<div class="w-full overflow-auto">
			<LoginBox
				:title="invitedBy ? 'Invitation to join' : 'Let\'s set up your account'"
				:subtitle="invitedBy ? `Invitation by ${invitedBy}` : ''"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="flex space-x-2">
						<img
							class="inline-block h-[38px] w-[38px] rounded-sm"
							:src="saasProduct?.logo"
						/>
					</div>
				</template>
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
							<template v-if="!userExists">
								<div class="flex gap-2">
									<FormControl
										label="First name"
										type="text"
										v-model="firstName"
										name="fname"
										autocomplete="given-name"
										variant="outline"
										required
										:disabled="Boolean(oauthSignup)"
									/>
									<FormControl
										label="Last name"
										type="text"
										v-model="lastName"
										name="lname"
										autocomplete="family-name"
										variant="outline"
										required
										:disabled="Boolean(oauthSignup)"
									/>
								</div>
							</template>
							<FormControl
								label="Email"
								type="text"
								:modelValue="email"
								variant="outline"
								disabled
							/>
							<FormControl
								type="select"
								:options="countries"
								v-if="!isInvitation"
								label="Country"
								v-model="country"
								variant="outline"
								required
							/>
							<FormControl
								v-if="!isInvitation"
								type="tel"
								label="Phone Number"
								v-model="phoneNumber"
								placeholder="9876543210"
								variant="outline"
							/>
						</div>
						<ErrorMessage
							class="mt-4"
							:message="$resources.setupAccount.error"
						/>
						<div v-if="showLeadsConsentCheckbox" class="mt-4 text-gray-600">
							<input
								id="share-details-consent"
								type="checkbox"
								class="rounded-sm mt-[1px] bg-surface-white border-outline-gray-4 text-ink-gray-9 hover:border-outline-gray-5 focus:ring-offset-0 focus:border-outline-gray-8 active:border-outline-gray-6 transition hover:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3 active:bg-surface-gray-2 w-3.5 h-3.5 checkbox"
								v-model="shareDetailsConsent"
							/>

							<label
								for="share-details-consent"
								class="ml-2 text-base font-normal"
								>Allow my details to be shared with a local partner</label
							>
						</div>
						<Button
							class="mt-4"
							variant="solid"
							:loading="
								$resources.setupAccount.loading ||
								$resources.acceptInvite.loading
							"
							type="submit"
						>
							{{
								is2FA ? 'Verify' : isInvitation ? 'Accept' : 'Create account'
							}}
						</Button>
					</template>
				</form>
				<div class="mt-4" v-if="!is2FA && !isInvitation">
					<span class="text-base font-normal text-gray-600">
						{{ 'By signing up, you agree to our ' }}
					</span>
					<a
						class="text-base font-normal text-gray-900 underline hover:text-gray-700"
						href="https://frappecloud.com/policies"
					>
						Terms & Policies
					</a>
				</div>
			</LoginBox>
		</div>
	</div>
	<div
		class="mt-20 px-6 text-center"
		v-else-if="!$resources.validateRequestKey.loading && !email"
	>
		Verification link or code is invalid or expired.
		<Link to="/signup">Sign up</Link>
		for a new account.
	</div>
	<div v-else></div>
</template>

<script>
import LoginBox from '../components/auth/LoginBox.vue';
import Link from '@/components/Link.vue';
import Form from '@/components/Form.vue';

const detailsSharedProducts = [
	'erpnext',
	'erpnextv15',
	'crm',
	'helpdesk',
	'hrms',
	'hrmsv15',
	'lending',
];

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
			invitedBy: null,
			invitedByParentTeam: false,
			countries: [],
			saasProduct: null,
			signupValues: {},
			detailsSharedProducts,
			shareDetailsConsent: false,
			phoneNumber: '',
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
					phone: this.phoneNumber || null,
					is_invitation: this.isInvitation,
					user_exists: this.userExists,
					invited_by_parent_team: this.invitedByParentTeam,
					oauth_signup: this.oauthSignup,
					oauth_domain: this.oauthDomain,
					share_details_consent:
						this.showLeadsConsentCheckbox && this.shareDetailsConsent,
				},
				onSuccess() {
					let path = '/dashboard/create-site/app-selector';
					if (this.saasProduct) {
						path = `/dashboard/create-site/${this.saasProduct.name}/setup`;
					}
					if (this.isInvitation) {
						path = '/dashboard/sites';
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
		acceptInvite() {
			return {
				url: 'press.api.account.accept_team_invite',
				params: {
					key: this.requestKey,
				},
				onSuccess() {
					this.$router.push({
						name: 'Site List',
					});
				},
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
		showLeadsConsentCheckbox() {
			return (
				this.saasProduct &&
				this.detailsSharedProducts.includes(this.saasProduct.name.toLowerCase())
			);
		},
	},
	methods: {
		submitForm() {
			if (this.invitedBy) {
				if (this.$session.isLoggedIn) {
					this.$resources.acceptInvite.submit();
				} else {
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
				}
			} else {
				this.$resources.setupAccount.submit();
			}
		},
	},
};
</script>
