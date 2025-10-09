<template>
	<div class="h-screen overflow-hidden">
		<LoginBox title="Log in to your site on Frappe Cloud" :subtitle="subtitle">
			<template v-slot:default>
				<div>
					<div v-if="sitePrePicked">
						<div v-if="loginError">
							<div class="flex items-center justify-center space-x-2 text-base">
								<FeatherIcon name="alert-triangle" class="mr-2 h-4 w-4" />
								<p>
									Something went wrong while attempting to log in to your site
								</p>
							</div>
							<div class="mx-4 mt-4 space-x-4">
								<Button
									label="Try again"
									icon-left="refresh-cw"
									:loading="login.loading"
									@click="loginToSite(pickedSite)"
								/>
								<Button
									label="View your sites"
									icon-left="list"
									:route="{
										name: 'Site Login',
									}"
								/>
							</div>
						</div>
						<div
							v-else-if="isPickedSiteValid"
							class="mt-8 flex flex-col items-center justify-center space-x-2 text-base"
						>
							<div class="flex items-center justify-center space-x-2 text-base">
								<FeatherIcon name="alert-circle" class="mr-2 h-4 w-4" />
								<div>
									<p>You are about to log in to your site</p>
									<span class="font-semibold">{{ pickedSiteDomain }}</span>
								</div>
							</div>
							<div class="mx-4 mt-8 space-x-4">
								<Button
									label="Log in"
									icon-left="log-in"
									variant="solid"
									:loading="login.loading"
									@click="loginToSite(pickedSite)"
								/>
							</div>
						</div>
					</div>
					<div
						v-else-if="
							$session.loading || isCookieValid.loading || sites.loading
						"
						class="mx-auto flex items-center justify-center space-x-2 text-base"
					>
						<LoadingText />
					</div>
					<form v-else-if="!sites.fetched">
						<FormControl
							label="Email"
							type="email"
							class="w-full"
							:class="{
								'pointer-events-none': showOTPField,
							}"
							v-model="email"
							placeholder="johndoe@mail.com"
						/>
						<FormControl
							v-if="showOTPField"
							label="Verification Code"
							v-model="otp"
							placeholder="123456"
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
								variant="outline"
								class="mt-2 w-full"
								:disabled="otpResendCountdown > 0"
								@click="sendOTP()"
								:loading="sendOTPMethod.loading"
							>
								Resend verification code
								{{
									otpResendCountdown > 0
										? `in ${otpResendCountdown} seconds`
										: ''
								}}
							</Button>
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
					<div v-else-if="pickedSite">
						<div
							class="mt-8 flex items-center justify-center space-x-2 text-base"
						>
							<FeatherIcon name="alert-triangle" class="mr-2 h-4 w-4" />
							<div class="flex flex-col gap-2">
								<p>
									{{ email || session.user }} is not a user of the site
									<span class="font-semibold">{{ pickedSite }}</span>
								</p>
							</div>
						</div>
						<div class="mt-8 flex w-full justify-center space-x-4">
							<Button
								label="View your sites"
								icon-left="list"
								@click="
									() => {
										$router.push({
											name: 'Site Login',
										});
									}
								"
							/>
						</div>
					</div>
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
											{{ site.host_name || site.name }}
										</div>
									</div>
									<FeatherIcon name="external-link" class="h-4 w-4" />
								</div>
							</div>
						</div>
					</div>

					<ErrorMessage
						class="mt-4"
						:message="
							sites.error || sendOTPMethod.error || verifyOTPMethod.error
						"
					/>
				</div>
			</template>
			<template v-slot:footer>
				<div class="flex w-full flex-col px-4 justify-center pb-8">
					<div v-if="sites.fetched">
						<span class="text-base font-normal text-gray-600">
							Switch to a different account?
						</span>
						<span
							class="text-base font-normal text-gray-900 underline hover:text-gray-700 cursor-pointer"
							@click="goBack"
						>
							Logout
						</span>
					</div>
					<div>
						<span class="text-base font-normal text-gray-600">
							Manage your sites?
						</span>
						<router-link
							class="text-base font-normal text-gray-900 underline hover:text-gray-700"
							:to="{
								name: 'Login',
							}"
						>
							Go to Frappe Cloud dashboard
						</router-link>
					</div>
				</div>
			</template>
		</LoginBox>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import { toast } from 'vue-sonner';
import { createResource } from 'frappe-ui';
import LoginBox from '../components/auth/LoginBox.vue';
import { getToastErrorMessage } from '../utils/toast';
import { trialDays } from '../utils/site';
import { userCurrency } from '../utils/format';
import { useRoute } from 'vue-router';
import { DashboardError } from '../utils/error';

const team = inject('team');
const session = inject('session');

const route = useRoute();
const pickedSite = computed(() => route.query.site);
const isPickedSiteValid = ref(false);

const email = ref(localStorage.getItem('product_site_user') || '');
const otp = ref('');
const showOTPField = ref(false);
const loginError = ref(false);
const otpResendCountdown = ref(0);

setInterval(() => {
	if (otpResendCountdown.value > 0) {
		otpResendCountdown.value -= 1;
	}
}, 1000);

const goBack = () => {
	sites.reset();
	showOTPField.value = false;
};

const isCookieValid = createResource({
	url: 'press.api.site_login.check_session_id',
	auto: !session.user,
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
	onSuccess: (data) => {
		if (pickedSite.value) {
			if (
				data.find((site) => site.name === pickedSite.value) ||
				data.find((site) => site.host_name === pickedSite.value)
			) {
				isPickedSiteValid.value = true;
			}
		}
	},
});

const login = createResource({
	url: 'press.api.site_login.login_to_site',
	onSuccess: (url) => {
		const newTab = pickedSite.value ? '_self' : '_blank';
		window.open(url, newTab);
	},
});

function loginToSite(siteName) {
	if (!siteName) {
		toast.error('Please select a site');
		return;
	}

	// avoid toast if user is coming from their site to login
	if (pickedSite.value)
		login.submit({
			email: email.value || session.user,
			site: siteName,
		});
	else
		toast.promise(
			login.submit({
				email: email.value || session.user,
				site: siteName,
			}),
			{
				loading: 'Logging in ...',
				success: 'Logged in',
				error: (e) => {
					loginError.value = true;
					return getToastErrorMessage(e);
				},
			},
		);
}

const sendOTPMethod = createResource({
	url: 'press.api.site_login.send_otp',
	validate: (data) => {
		if (!data.email) {
			throw new DashboardError('Please enter email');
		}
		if (!data.email.match(/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/)) {
			throw new DashboardError('Please enter a valid email');
		}
	},
	onSuccess: () => {
		showOTPField.value = true;
		otpResendCountdown.value = 30;
		if (email.value) localStorage.setItem('site_login_email', email.value);
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
		sites.submit({
			user: email.value,
		});
		otp.value = '';
		sendOTPMethod.error = '';
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

const subtitle = computed(() => {
	if (pickedSite.value && sites.fetched && sites.data.length !== 0) return '';
	else if (sites.fetched && sites.data.length !== 0)
		return `Pick a site to log in to as ${email.value || session.user}`;
	else if (
		!sites.fetched &&
		!(sites.loading || isCookieValid.loading || session.loading)
	)
		return 'Enter your email to access your site';
	else return '';
});

const sitePrePicked = computed(() => {
	if (pickedSite.value && sites.fetched && sites.data.length !== 0) {
		return sites.data.find(
			(site) =>
				site.name === pickedSite.value || site.host_name === pickedSite.value,
		);
	}
	return false;
});

const pickedSiteDomain = computed(() => {
	if (sitePrePicked.value)
		return sitePrePicked.value.host_name || sitePrePicked.value.name;
	return '';
});
</script>
