<template>
	<div>
		<LoginBox
			v-if="!emailSent"
			title="Create your account"
			:class="{ 'pointer-events-none': $resources.signup.loading }"
		>
			<template #logo v-if="saasProduct">
				<div class="mx-auto flex flex-col items-center">
					<img
						class="mb-1"
						v-if="saasProduct.logo"
						:src="saasProduct.logo"
						:alt="saasProduct.title"
					/>
					<div class="text-5xl font-semibold text-gray-900" v-else>
						{{ saasProduct.title }}
					</div>
					<div class="text-base text-gray-700">Powered by Frappe Cloud</div>
				</div>
			</template>
			<form class="flex flex-col" @submit.prevent="$resources.signup.submit()">
				<FormControl
					label="Email"
					type="email"
					placeholder="johndoe@mail.com"
					autocomplete="email"
					v-model="email"
					required
				/>
				<ErrorMessage class="mt-2" :message="$resources.signup.error" />
				<Button
					class="mt-2"
					:loading="$resources.signup.loading"
					variant="solid"
				>
					Sign up with email
				</Button>
				<div class="-mb-2 mt-6 border-t text-center">
					<div class="-translate-y-1/2 transform">
						<span
							class="bg-white px-2 text-xs uppercase leading-8 tracking-wider text-gray-800"
						>
							Or
						</span>
					</div>
				</div>
			</form>
			<div class="flex flex-col">
				<Button
					v-if="$resources.signupSettings.data?.enable_google_oauth === 1"
					:loading="$resources.oauthLogin.loading"
					@click="$resources.oauthLogin.submit()"
				>
					<div class="flex">
						<GoogleIcon />
						<span class="ml-2">Sign up with Google</span>
					</div>
				</Button>
				<router-link class="mt-10 text-center text-base" to="/login">
					Already have an account? Log in.
				</router-link>
			</div>
		</LoginBox>
		<SuccessCard
			class="mx-auto mt-20 w-96 shadow-md"
			title="Verification Email Sent!"
			v-else
		>
			We have sent an email to
			<span class="font-semibold">{{ email }}</span
			>. Please click on the link received to verify your email and set up your
			account.
		</SuccessCard>
	</div>
</template>

<script>
import LoginBox from '@/views/partials/LoginBox.vue';
import GoogleIcon from '@/components/icons/GoogleIcon.vue';

export default {
	name: 'Signup',
	components: {
		LoginBox,
		GoogleIcon
	},
	data() {
		return {
			email: null,
			emailSent: false
		};
	},
	resources: {
		signup() {
			return {
				method: 'press.api.account.signup',
				params: {
					email: this.email,
					referrer: this.getReferrerIfAny(),
					product: this.$route.query.product
				},
				onSuccess() {
					this.emailSent = true;
					//window.posthog.capture(
					//'init_client_fc_account_email_sent',
					//'fc_setup'
					//);
				}
			};
		},
		oauthLogin() {
			return {
				method: 'press.api.oauth.google_login',
				onSuccess(r) {
					window.location = r;
				}
			};
		},
		signupSettings() {
			return {
				method: 'press.api.account.signup_settings',
				params: {
					product: this.$route.query.product
				},
				auto: true
			};
		}
	},
	methods: {
		getReferrerIfAny() {
			const params = location.search;
			const searchParams = new URLSearchParams(params);
			return searchParams.get('referrer');
		}
	},
	computed: {
		saasProduct() {
			return this.$resources.signupSettings.data?.saas_product;
		}
	}
};
</script>
