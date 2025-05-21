<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="$resources.signupSettings.loading"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50" v-else>
		<div class="w-full overflow-auto">
			<LoginBox
				title="Get started in minutes"
				subtitle="14 days free trial, no credit card required."
				:class="{ 'pointer-events-none': $resources.setupAccount?.loading }"
				:logo="saasProduct?.logo"
			>
				<template v-slot:default>
					<form
						class="flex flex-col"
						@submit.prevent="this.$resources.setupAccount.submit()"
					>
						<!-- Fields -->
						<FormControl
							label="Email"
							type="email"
							placeholder="johndoe@mail.com"
							variant="outline"
							autocomplete="email"
							v-model="email"
							required
							disabled
						/>
						<FormControl
							class="mt-5"
							label="Country"
							type="select"
							placeholder="Select your country"
							autocomplete="country"
							variant="outline"
							:options="countries"
							v-model="country"
							required
						/>
						<div class="mt-5 text-base">
							<label class="leading-6 tracking-normal">
								<FormControl
									type="checkbox"
									v-model="terms_accepted"
									class="mr-0.5 py-1 align-baseline"
								/>
								I agree to Frappe&nbsp;
								<Link href="https://frappecloud.com/terms" target="_blank">
									Terms of Service </Link
								>,&nbsp;
								<Link href="https://frappecloud.com/privacy" target="_blank">
									Privacy Policy
								</Link>
								&nbsp;&&nbsp;
								<Link
									href="https://frappecloud.com/cookie-policy"
									target="_blank"
								>
									Cookie Policy
								</Link>
							</label>
						</div>
						<!-- Error Message -->
						<ErrorMessage
							class="mt-2"
							:message="this.$resources?.setupAccount?.error"
						/>
						<!-- Buttons -->
						<div class="mt-8 flex flex-col items-center gap-3">
							<Button
								:loading="$resources.setupAccount?.loading || isRedirecting"
								variant="solid"
								class="w-full font-medium"
								type="submit"
							>
								Create Account
							</Button>
						</div>
					</form>
				</template>
			</LoginBox>
		</div>
	</div>
</template>
<script>
import { Spinner } from 'frappe-ui';
import LoginBox from '../../components/auth/SaaSLoginBox.vue';

export default {
	name: 'SaaSSignupOAuthSetupAccount',
	props: ['productId'],
	components: {
		LoginBox,
		Spinner,
	},
	data() {
		return {
			key: this.$route.query.key,
			email: this.$route.query.email,
			country: null,
			terms_accepted: false,
			isRedirecting: false,
		};
	},
	resources: {
		setupAccount() {
			return {
				url: 'press.api.product_trial.setup_account',
				makeParams() {
					return {
						key: this.key,
						country: this.country,
					};
				},
				onSuccess: (data) => {
					this.isRedirecting = true;
					window.location.href = data?.location;
				},
			};
		},
		signupSettings() {
			return {
				url: 'press.api.account.signup_settings',
				params: {
					product: this.productId,
					fetch_countries: true,
					timezone: window.Intl
						? Intl.DateTimeFormat().resolvedOptions().timeZone
						: null,
				},
				auto: true,
				onSuccess(res) {
					if (res && res.country) {
						this.country = res.country;
					}
				},
			};
		},
	},
	computed: {
		saasProduct() {
			return this.$resources.signupSettings.data?.product_trial;
		},
		countries() {
			return this.$resources.signupSettings.data?.countries || [];
		},
	},
};
</script>
