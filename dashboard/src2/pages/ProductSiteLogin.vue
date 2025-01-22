<template>
	<div class="h-full sm:bg-gray-50">
		<div class="flex w-full items-center justify-center" v-if="false">
			<Spinner class="mr-2 w-4" />
			<p class="text-gray-800">Loading</p>
		</div>
		<div class="flex" v-else>
			<div class="h-full w-full overflow-auto">
				<SaaSLoginBox
					title="Welcome to Frappe Cloud"
					:subtitle="[`Enter your email address to access your site.`]"
				>
					<template v-slot:default>
						<div class="space-y-4">
							<form
								class="flex space-x-2"
								@submit.prevent="
									sites.submit({
										user: email
									})
								"
							>
								<FormControl
									label="Email"
									class="w-full"
									v-model="email"
									variant="outline"
								/>
								<Button
									label="Submit"
									:disabled="email.length === 0"
									variant="solid"
									class="mt-5"
								/>
							</form>
							<ErrorMessage :message="sites.error" />
							<ObjectList v-if="sites.fetched" :options="siteListOptions" />
						</div>
					</template>
				</SaaSLoginBox>
				<div class="flex w-full items-center justify-center pb-2">
					<Button
						class="mt-4"
						@click="
							$router.push({
								name: 'Login'
							})
						"
						icon-right="arrow-right"
						variant="ghost"
						:label="
							$session.user
								? 'Go to Frappe Cloud Dashboard'
								: 'Login to Frappe Cloud Dashboard'
						"
					/>
				</div>
			</div>
		</div>
	</div>
	<Dialog
		:options="{
			title: `Verification to access the site`,
			actions: [
				{ label: 'Verify', variant: 'solid', onClick: verifyOTP },
				{
					label: 'Resend verification code',
					variant: 'outline',
					onClick: resendOTP
				}
			]
		}"
		v-model="showOTPDialog"
	>
		<template v-slot:body-content>
			<FormControl
				label="Enter verification code"
				v-model="otp"
				variant="outline"
			/>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, inject, ref } from 'vue';
import { toast } from 'vue-sonner';
import { get, set } from 'idb-keyval';
import { createResource, createDocumentResource } from 'frappe-ui';
import SaaSLoginBox from '../components/auth/SaaSLoginBox.vue';
import { getToastErrorMessage } from '../utils/toast';
import ObjectList from '../components/ObjectList.vue';
import { trialDays } from '../utils/site';
import { userCurrency } from '../utils/format';
import { useRoute } from 'vue-router';

const team = inject('team');

const route = useRoute();
const productName = route.params.product;

// const email = defineModel({
// 	default: '',
// 	type: String
// });
// const otp = defineModel({
// 	default: '',
// 	type: String
// });
// const showOTPDialog = defineModel({
// 	default: false,
// 	type: Boolean
// });
const email = ref('');
const otp = ref('');
const showOTPDialog = ref(false);
const selectedSite = ref(null);

get('product_site_user').then(e => {
	if (e) {
		email.value = e;
	}
});

const product = createDocumentResource({
	doctype: 'Product',
	name: productName,
	fields: ['title', 'image'],
	auto: !!productName
});

const sites = createResource({
	url: 'press.api.product_trial.get_product_sites_of_user',
	doctype: 'Site',
	onSuccess: () => {
		if (email.value) set('product_site_user', email.value);
	}
});

const siteListOptions = computed(() => {
	return {
		data: () => sites.data || [],
		hideControls: true,
		emptyStateMessage: sites.loading
			? 'Fetching sites...'
			: `No sites found for ${sites?.params?.user}.`,
		onRowClick: row => {
			selectedSite.value = row;
			showOTPDialog.value = true;

			sendOTP();
		},
		columns: [
			{
				label: 'Site',
				fieldname: 'site_label',
				format: (_, row) => row.site_label || row.name
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
							0
						);
						return `${formattedValue}/mo`;
					}
					return row.plan_title;
				}
			}
		]
	};
});

function loginToSite(siteName) {
	if (!siteName) {
		toast.error('Please select a site');
		return;
	}

	const login = createResource({
		url: 'press.api.product_trial.login_to_site',
		params: {
			email: email.value,
			site: siteName
		},
		onSuccess: url => {
			window.open(url, '_blank');
		}
	});

	toast.promise(login.submit(), {
		loading: 'Logging in ...',
		success: 'Logged in',
		error: e => getToastErrorMessage(e)
	});
}

const sendOTPMethod = createResource({
	url: 'press.api.product_trial.send_otp'
});

function sendOTP() {
	if (!email.value) {
		toast.error('Please enter email');
		return;
	}

	toast.promise(
		sendOTPMethod.submit({
			email: email.value,
			site: selectedSite.value.name
		}),
		{
			loading: 'Sending OTP ...',
			success: `OTP sent to ${email.value}`,
			error: e => getToastErrorMessage(e)
		}
	);
}

function resendOTP() {
	if (!email.value) {
		toast.error('Please enter email');
		return;
	}

	toast.promise(
		sendOTPMethod.submit({
			email: email.value,
			site: selectedSite.value.name
		}),
		{
			loading: 'Resending OTP ...',
			success: `OTP resent to ${email.value}`,
			error: e => getToastErrorMessage(e)
		}
	);
}

function verifyOTP() {
	if (!otp.value) {
		toast.error('Please enter OTP');
		return;
	}

	const verifyOTP = createResource({
		url: 'press.api.product_trial.verify_otp',
		params: {
			email: email.value,
			site: selectedSite.value.name,
			otp: otp.value
		},
		onSuccess: () => {
			showOTPDialog.value = false;
			loginToSite(selectedSite.value.name);
			otp.value = '';
		}
	});

	toast.promise(verifyOTP.submit(), {
		loading: 'Verifying OTP ...',
		success: 'OTP verified',
		error: e => getToastErrorMessage(e)
	});
}
</script>
