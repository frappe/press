<template>
	<LoginBox
		v-if="!emailSent"
		title="Create your account"
		:class="{ 'pointer-events-none': $resources.signup.loading }"
	>
		<form class="flex flex-col" @submit.prevent="$resources.signup.submit()">
			<Input
				label="Email"
				type="email"
				placeholder="johndoe@mail.com"
				autocomplete="email"
				v-model="email"
				required
			/>
			<ErrorMessage class="mt-4" :message="$resources.signup.error" />
			<Button class="mt-6" :loading="$resources.signup.loading" variant="solid">
				Submit
			</Button>
			<div class="mt-10 border-t text-center">
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
				v-if="
					$resources.guestFeatureFlags.data &&
					$resources.guestFeatureFlags.data.enable_google_oauth === 1
				"
				:loading="$resources.oauthLogin.loading"
				@click="
					() => {
						state = 'RequestStarted';
						$resources.oauthLogin.submit();
					}
				"
			>
				<div class="flex">
					<GoogleIcon />
					<span class="ml-2">Signup with Google</span>
				</div>
			</Button>
			<router-link class="text-center text-base mt-4" to="/login">
				Already have an account? Log in.
			</router-link>
		</div>
	</LoginBox>
	<SuccessCard
		class="mx-auto mt-20 w-96 shadow-md sm:ml-auto sm:mr-auto"
		title="Verification Email Sent!"
		v-else
	>
		We have sent an email to
		<span class="font-semibold">{{ email }}</span
		>. Please click on the link received to verify your email and set up your
		account.
	</SuccessCard>
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
					referrer: this.getReferrerIfAny()
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
		guestFeatureFlags() {
			return {
				method: 'press.api.account.guest_feature_flags',
				auto: true
			};
		}
	},
	mounted() {
		this.$resources.guestFeatureFlags.submit();
	},
	methods: {
		getReferrerIfAny() {
			const params = location.search;
			const searchParams = new URLSearchParams(params);

			return searchParams.get('referrer');
		}
	}
};
</script>
