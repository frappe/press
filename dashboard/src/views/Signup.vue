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
			<ErrorMessage class="mt-4" :error="$resources.signup.error" />
			<Button class="mt-6" :loading="$resources.signup.loading" type="primary">
				Submit
			</Button>
			<div class="mt-10 text-center border-t">
				<div class="transform -translate-y-1/2">
					<span
						class="px-2 text-xs leading-8 tracking-wider text-gray-800 uppercase bg-white"
					>
						Or
					</span>
				</div>
			</div>
			<router-link class="text-base text-center" to="/login">
				Already have an account? Log in.
			</router-link>
		</form>
	</LoginBox>
	<SuccessCard
		class="mx-auto mt-20 shadow-md w-96"
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
import LoginBox from './partials/LoginBox.vue';

export default {
	name: 'Signup',
	components: {
		LoginBox
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
				}
			};
		}
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
