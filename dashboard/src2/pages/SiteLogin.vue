<template>
	<div class="h-screen overflow-hidden sm:bg-gray-50">
		<LoginBox
			title="Log in to your site on Frappe Cloud"
			:subtitle="[
				sites.fetched && sites.data.length !== 0
					? `Pick a site to login to as ${email || $session.user}`
					: !sites.fetched
						? 'Enter your email and verification code to access your site'
						: '',
			]"
		>
			<template v-slot:default>
				<div>
					<div
						v-if="$session.loading || isCookieValid.loading || sites.loading"
						class="mx-auto flex items-center justify-center space-x-2 text-base"
					>
						<LoadingText />
					</div>
					<form v-else-if="!sites.fetched">
						<FormControl
							label="Email"
							class="w-full"
							v-model="email"
							placeholder="johndoe@mail.com"
						/>
						<FormControl
							v-if="showOTPField"
							label="Verification Code"
							v-model="otp"
							class="mt-2"
						/>
						<div v-if="showOTPField">
							<Button
								label="Verify"
								:disabled="otp.length !== 6"
								:loading="
									sites.loading ||
									sendOTPMethod.loading ||
									verifyOTPMethod.loading
								"
								variant="solid"
								class="mt-4 w-full"
								@click="verifyOTP"
							/>
							<Button
								label="Resend Verification Code"
								variant="outline"
								class="mt-2 w-full"
								@click="sendOTP()"
								:loading="sendOTPMethod.loading"
							/>
						</div>
						<Button
							v-else
							label="Submit"
							:disabled="email.length === 0"
							:loading="
								sites.loading ||
								sendOTPMethod.loading ||
								verifyOTPMethod.loading
							"
							variant="solid"
							class="mt-4 w-full"
							@click="sendOTP"
						/>
					</form>
					<div v-else class="mt-10">
						<div v-if="sites.data.length === 0">
							<div class="text-center text-base leading-6 text-gray-700">
								<div>No sites found for {{ email }}</div>
								<Link :to="{ name: 'Signup' }">Sign up</Link> to create a new
								site
							</div>
						</div>
						<div class="space-y-2" v-else>
							<div
								v-for="site in sites.data"
								:key="site.name"
								class="flex items-center justify-between rounded-md px-3 py-2 hover:cursor-pointer hover:bg-gray-100"
								@click="loginToSite(site.name)"
							>
								<div
									class="flex min-h-[40px] w-full items-center justify-between"
								>
									<div class="space-y-2">
										<div class="text-base text-gray-800">
											{{ site.site_label || site.name }}
										</div>
										<div v-if="site.site_label" class="text-sm text-gray-600">
											{{ site.name }}
										</div>
									</div>
									<FeatherIcon name="external-link" class="h-4 w-4" />
								</div>
							</div>
						</div>
					</div>

					<ErrorMessage
						:message="
							sites.error || sendOTPMethod.error || verifyOTPMethod.error
						"
					/>
				</div>
			</template>
			<template v-slot:footer>
				<div
					class="flex w-full flex-col items-center justify-center space-y-2 pb-8"
				>
					<Button
						v-if="$session.user && !sites.fetched"
						class="mt-4"
						@click="
							$router.push({
								name: 'Login',
							})
						"
						icon-right="arrow-right"
						variant="ghost"
						label="Go to Frappe Cloud dashboard"
					/>
					<Button
						v-if="sites.fetched"
						class="mt-4"
						@click="goBack"
						icon-right="arrow-left"
						variant="ghost"
						label="Login from another account"
					/>
				</div>
			</template>
		</LoginBox>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import { toast } from 'vue-sonner';
import { get, set } from 'idb-keyval';
import { createResource } from 'frappe-ui';
import LoginBox from '../components/auth/LoginBox.vue';
import { getToastErrorMessage } from '../utils/toast';
import { trialDays } from '../utils/site';
import { userCurrency } from '../utils/format';

const team = inject('team');
const session = inject('session');

const email = ref('');
const otp = ref('');
const showOTPField = ref(false);
const selectedSite = ref(null);

get('product_site_user').then((e) => {
	if (e) {
		email.value = e;
	}
});

const goBack = () => {
	sites.reset();
	showOTPField.value = false;
};

const isCookieValid = createResource({
	url: 'press.api.site_login.check_session_id',
	auto: true,
	onSuccess: (session_user_email) => {
		if (session_user_email) {
			email.value = session_user_email;
			sites.submit({
				user: session_user_email,
			});
		}
	},
});

const sites = createResource({
	url: 'press.api.site_login.get_product_sites_of_user',
	doctype: 'Site',
	auto: session.user,
	params: {
		user: email.value || session.user,
	},
});

const login = createResource({
	url: 'press.api.site_login.login_to_site',
	onSuccess: (url) => {
		window.open(url, '_blank');
	},
});

function loginToSite(siteName) {
	if (!siteName) {
		toast.error('Please select a site');
		return;
	}

	toast.promise(
		login.submit({
			email: email.value,
			site: siteName,
		}),
		{
			loading: 'Logging in ...',
			success: 'Logged in',
			error: (e) => getToastErrorMessage(e),
		},
	);
}

const sendOTPMethod = createResource({
	url: 'press.api.site_login.send_otp',
	onSuccess: () => {
		showOTPField.value = true;
		if (email.value) set('product_site_user', email.value);
	},
});

function sendOTP() {
	if (!email.value) {
		toast.error('Please enter email');
		return;
	}

	toast.promise(
		sendOTPMethod.submit({
			email: email.value,
		}),
		{
			loading: 'Sending OTP ...',
			success: `OTP sent to ${email.value}`,
			error: (e) => getToastErrorMessage(e),
		},
	);
}

const verifyOTPMethod = createResource({
	url: 'press.api.site_login.verify_otp',
	onSuccess: () => {
		// showOTPField.value = false;
		sites.submit({
			user: email.value,
		});
		// loginToSite(selectedSite.value.name);
		otp.value = '';
	},
});

function verifyOTP() {
	if (!otp.value) {
		toast.error('Please enter OTP');
		return;
	}

	toast.promise(
		verifyOTPMethod.submit({
			email: email.value,
			otp: otp.value,
		}),
		{
			loading: 'Verifying OTP ...',
			success: 'OTP verified',
			error: (e) => getToastErrorMessage(e),
		},
	);
}

function planTitle(site) {
	if (site.trial_end_date) return trialDays(site.trial_end_date);
	if (site.price_usd > 0 && team) {
		const india = team?.doc?.currency === 'INR';
		const formattedValue = userCurrency(
			india ? site.price_inr : site.price_usd,
			0,
		);
		return `${formattedValue}/mo`;
	}
	return site.plan_title;
}
</script>
