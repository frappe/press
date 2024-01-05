<template>
	<div
		class="flex h-screen overflow-hidden bg-gray-50"
		v-if="!$resources.validateRequestKey.loading && email"
	>
		<ProductSignupPitch :saasProduct="saasProduct" class="w-[40%]" />
		<div class="w-full overflow-auto">
			<LoginBox
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
						<Form
							v-if="signupFields.length > 0"
							:fields="signupFields"
							v-model="signupValues"
						/>
						<div class="mt-4 flex items-start">
							<label class="text-base text-gray-900">
								<FormControl type="checkbox" v-model="termsAccepted" />
								By clicking on
								<span>{{ isInvitation ? 'Accept' : 'Create account' }}</span
								>, you accept our
								<Link href="https://frappecloud.com/terms" target="_blank"
									>Terms of Service </Link
								>,
								<Link href="https://frappecloud.com/privacy" target="_blank">
									Privacy Policy
								</Link>
								&#38;
								<Link
									href="https://frappecloud.com/cookie-policy"
									target="_blank"
								>
									Cookie Policy
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
import LoginBox from '@/views/partials/LoginBox.vue';
import Link from '@/components/Link.vue';
import Form from '@/components/Form.vue';
import ProductSignupPitch from '../components/ProductSignupPitch.vue';

export default {
	name: 'SetupAccount',
	components: {
		LoginBox,
		Link,
		Form,
		ProductSignupPitch
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
			saasProduct: null,
			signupValues: {}
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
						: null
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
					signup_values: this.signupValues
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
	},
	computed: {
		signupFields() {
			let fields = this.saasProduct?.signup_fields || [];
			return fields.map(df => {
				if (df.fieldtype == 'Select') {
					df.options = df.options
						.split('\n')
						.map(o => o.trim())
						.filter(Boolean);
				}
				df.required = true;
				return df;
			});
		}
	}
};
</script>
