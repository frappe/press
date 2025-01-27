<template>
	<div class="h-full sm:bg-gray-50">
		<div class="flex w-full items-center justify-center" v-if="false">
			<Spinner class="mr-2 w-4" />
			<p class="text-gray-800">Loading</p>
		</div>
		<div class="flex" v-else>
			<div class="h-full w-full overflow-auto">
				<SaaSLoginBox
					title="Login to your site on Frappe Cloud"
					:subtitle="[
						sites.fetched
							? `Pick a site to login to as ${email || $session.user}`
							: 'Enter your email and verification code to access your site',
					]"
				>
					<template v-slot:default>
						<div class="space-y-4">
							<div
								v-if="$session.loading || isCookieValid.loading"
								class="mx-auto flex items-center justify-center space-x-2 text-base"
							>
								<LoadingText />
							</div>
							<form v-else-if="!sites.fetched">
								<FormControl
									label="Email"
									class="w-full"
									v-model="email"
									variant="outline"
								/>
								<FormControl
									v-if="showOTPField"
									label="Verification Code"
									v-model="otp"
									variant="outline"
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
							<div v-else>
								<ObjectList :options="siteListOptions" />
							</div>

							<ErrorMessage
								:message="
									sites.error || sendOTPMethod.error || verifyOTPMethod.error
								"
							/>
						</div>
					</template>
				</SaaSLoginBox>
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
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import { toast } from 'vue-sonner';
import { get, set } from 'idb-keyval';
import { createResource } from 'frappe-ui';
import SaaSLoginBox from '../components/auth/SaaSLoginBox.vue';
import { getToastErrorMessage } from '../utils/toast';
import ObjectList from '../components/ObjectList.vue';
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

const getCookie = (name) => {
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);

	if (parts.length === 2) return parts.pop().split(';').shift();
};

const setCookie = (name, value, days) => {
	const date = new Date();
	date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000); // 24 hours
	const expires = `expires=${date.toUTCString()}`;
	document.cookie = `${name}=${value};${expires};path=/`;
};

const deleteCookie = (name) => {
	document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
};

const goBack = () => {
	sites.reset();
	showOTPField.value = false;
};

const isCookieValid = createResource({
	url: 'press.api.site_login.check_session_id',
	auto: !!getCookie('site_user_sid'),
	onSuccess: (session_user_email) => {
		if (session_user_email) {
			email.value = session_user_email;
			sites.submit({
				user: session_user_email,
			});
		} else {
			deleteCookie('site_user_sid');
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

const siteListOptions = computed(() => {
	return {
		data: () => sites.data || [],
		hideControls: true,
		emptyStateMessage: sites.loading
			? 'Fetching sites...'
			: `No sites found for ${sites?.params?.user}.`,
		onRowClick: (row) => {
			loginToSite(row.name);
			selectedSite.value = row;
		},
		columns: [
			{
				label: 'Site',
				fieldname: 'site_label',
				format: (_, row) => row.site_label || row.name,
			},
			{
				label: '',
				fieldname: 'trial_end_date',
				align: 'right',
				class: ' text-sm',
				format: (value, row) => {
					if (value) return trialDays(value);
					if (row.price_usd > 0 && team) {
						const india = team?.doc?.currency === 'INR';
						const formattedValue = userCurrency(
							india ? row.price_inr : row.price_usd,
							0,
						);
						return `${formattedValue}/mo`;
					}
					return row.plan_title;
				},
			},
		],
	};
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
</script>
