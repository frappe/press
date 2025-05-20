<template>
	<div
		class="flex h-screen overflow-hidden"
		v-if="!$resources.validateRequestKey.loading && email"
	>
		<div class="w-full overflow-auto">
			<LoginBox
				:title="invitedBy ? 'Invitation to join' : 'Let\'s set up your site'"
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
							<div v-if="!isInvitation" class="w-full space-y-1.5">
								<div class="flex items-center gap-2">
									<label class="block text-xs text-ink-gray-5">
										Site name
									</label>
									<Tooltip
										text="You will be able to access your site via your site name"
									>
										<i-lucide-info class="h-4 w-4 text-gray-500" />
									</Tooltip>
								</div>
								<div class="col-span-2 flex w-full">
									<input
										class="dark:[color-scheme:dark] z-10 h-7 w-full rounded rounded-r-none border border-outline-gray-2 bg-surface-white py-1.5 pl-2 pr-2 text-base text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-3 hover:shadow-sm focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
										:placeholder="
											saasProduct ? `${saasProduct?.name}-site` : 'company-name'
										"
										v-model="subdomain"
									/>
									<div
										class="flex cursor-default items-center rounded-r bg-gray-100 px-2 text-base"
									>
										.{{ domain }}
									</div>
								</div>
								<div class="mt-1">
									<div
										v-if="$resources.subdomainExists.loading"
										class="text-sm text-gray-600"
									>
										Checking...
									</div>
									<template
										v-else-if="
											!$resources.subdomainExists.error &&
											$resources.subdomainExists.fetched &&
											subdomain
										"
									>
										<div
											v-if="$resources.subdomainExists.data"
											class="text-sm text-green-600"
										>
											{{ subdomain }}.{{ domain }} is available
										</div>
										<div v-else class="text-sm text-red-600">
											{{ subdomain }}.{{ domain }} is not available
										</div>
									</template>
									<ErrorMessage :message="$resources.subdomainExists.error" />
								</div>
							</div>
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
						</div>
						<ErrorMessage
							class="mt-4"
							:message="$resources.setupAccount.error"
						/>
						<Button
							class="mt-4"
							variant="solid"
							:loading="$resources.setupAccount.loading"
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
		Verification link is invalid or expired.
		<Link to="/signup">Sign up</Link>
		for a new account.
	</div>
	<div v-else></div>
</template>

<script>
import { debounce } from 'frappe-ui';
import LoginBox from '../components/auth/LoginBox.vue';
import Link from '@/components/Link.vue';
import Form from '@/components/Form.vue';
import { validateSubdomain } from '../utils/site';
import { DashboardError } from '../utils/error';

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
			subdomain: '',
			defaultDomain: '',
		};
	},
	watch: {
		subdomain: {
			handler: debounce(function () {
				this.$resources.subdomainExists.submit();
			}, 500),
		},
	},
	resources: {
		subdomainExists() {
			return {
				url: 'press.api.site.exists',
				makeParams() {
					return {
						domain: this.domain,
						subdomain: this.subdomain,
					};
				},
				validate() {
					const error = validateSubdomain(this.subdomain);
					if (error) {
						throw new DashboardError(error);
					}
				},
				transform(data) {
					return !Boolean(data);
				},
			};
		},
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
						this.defaultDomain = res.default_domain;
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
					oauth_signup: this.oauthSignup,
					oauth_domain: this.oauthDomain,
					site_domain: `${this.subdomain}.${this.domain}`,
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
		domain() {
			return this.saasProduct?.domain || this.defaultDomain;
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
