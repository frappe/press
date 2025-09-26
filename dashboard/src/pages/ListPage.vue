<template>
	<div class="flex h-full flex-col">
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<Breadcrumbs
					:items="[{ label: object.list.title, route: object.list.route }]"
				/>
			</Header>
		</div>
		<div class="p-5">
			<AlertAddPaymentMode
				class="mb-5"
				v-if="$team?.doc && !$team.doc.payment_mode && !$team.doc.parent_team"
			/>
			<AlertCardExpired
				class="mb-5"
				v-if="$team?.doc && isCardExpired && $team.doc?.payment_mode == 'Card'"
			/>
			<AlertAddressDetails
				class="mb-5"
				v-if="
					$team?.doc &&
					!$team.doc?.billing_details?.name &&
					$team.doc.payment_mode
				"
			/>
			<AlertBanner
				v-for="banner in localBanners"
				class="mb-5"
				:key="banner.name"
				:title="`<b>${banner.title}:</b> ${banner.message}`"
				:type="banner.type.toLowerCase()"
				:isDismissible="banner.is_dismissible"
				@dismissBanner="closeBanner(banner.name)"
			>
				<template v-if="!!banner.help_url">
					<Button
						class="ml-auto flex flex-row items-center gap-1"
						@click="openHelp(banner.help_url)"
						variant="outline"
					>
						Open help
						<lucide-external-link class="inline h-4 w-3 pb-0.5" />
					</Button>
				</template>
			</AlertBanner>
			<AlertMandateInfo
				class="mb-5"
				v-if="
					$team?.doc &&
					isMandateNotSet &&
					$team.doc.currency === 'INR' &&
					$team.doc.payment_mode == 'Card'
				"
			/>
			<AlertUnpaidInvoices
				class="mb-5"
				v-if="
					hasUnpaidInvoices > 0 && $team.doc.payment_mode == 'Prepaid Credits'
				"
				:amount="hasUnpaidInvoices"
			/>
			<ObjectList :options="listOptions" />
		</div>
	</div>
</template>

<script>
import Header from '../components/Header.vue';
import ObjectList from '../components/ObjectList.vue';
import { Breadcrumbs, Button, Dropdown, TextInput } from 'frappe-ui';
import { getObject } from '../objects';
import { defineAsyncComponent } from 'vue';
import dayjs from '../utils/dayjs';
import AlertBanner from '../components/AlertBanner.vue';

export default {
	components: {
		Header,
		Breadcrumbs,
		ObjectList,
		Button,
		Dropdown,
		TextInput,
		AlertBanner,
		AlertAddPaymentMode: defineAsyncComponent(
			() => import('../components/AlertAddPaymentMode.vue'),
		),
		AlertCardExpired: defineAsyncComponent(
			() => import('../components/AlertCardExpired.vue'),
		),
		AlertAddressDetails: defineAsyncComponent(
			() => import('../components/AlertAddressDetails.vue'),
		),
		AlertMandateInfo: defineAsyncComponent(
			() => import('../components/AlertMandateInfo.vue'),
		),
		AlertUnpaidInvoices: defineAsyncComponent(
			() => import('../components/AlertUnpaidInvoices.vue'),
		),
	},
	props: {
		objectType: {
			type: String,
			required: true,
		},
	},
	data() {
		return {
			localBanners: [],
		};
	},
	methods: {
		getRoute(row) {
			return {
				name: `${this.object.doctype} Detail`,
				params: {
					name: row.name,
				},
			};
		},
		closeBanner(bannerName) {
			this.localBanners = this.localBanners.filter(
				(b) => b.name !== bannerName,
			);
			this.$resources.dismissBanner.submit({
				banner_name: bannerName,
			});
		},
		openHelp(url) {
			window.open(url, '_blank');
		},
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
		listOptions() {
			return {
				...this.object.list,
				doctype: this.object.doctype,
				route: this.object.detail ? this.getRoute : null,
			};
		},
		isCardExpired() {
			if (this.$team.doc.payment_method?.expiry_year < dayjs().year()) {
				return true;
			} else if (
				this.$team.doc.payment_method?.expiry_year == dayjs().year() &&
				this.$team.doc.payment_method?.expiry_month < dayjs().month() + 1
			) {
				return true;
			} else {
				return false;
			}
		},
		banners() {
			return this.$resources.banners.data || [];
		},
		isMandateNotSet() {
			return !this.$team.doc?.payment_method?.stripe_mandate_id;
		},
		hasUnpaidInvoices() {
			return this.$resources.getAmountDue.data;
		},
	},
	resources: {
		banners() {
			return {
				url: 'press.press.doctype.dashboard_banner.dashboard_banner.get_user_banners',
				auto: true,
				onSuccess: (data) => {
					this.localBanners = data;
				},
			};
		},
		getAmountDue() {
			return {
				url: 'press.api.billing.total_unpaid_amount',
				auto: true,
			};
		},
		dismissBanner() {
			return {
				url: 'press.press.doctype.dashboard_banner.dashboard_banner.dismiss_banner',
				auto: false,
			};
		},
	},
};
</script>
