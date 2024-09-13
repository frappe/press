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
				v-if="banner?.enabled"
				class="mb-5"
				:title="`<b>${banner.title}:</b> ${banner.message}`"
				:type="banner.type.toLowerCase()"
			/>
			<AlertMandateInfo
				class="mb-5"
				v-if="
					$team?.doc &&
					isMandateNotSet &&
					$team.doc.currency === 'INR' &&
					$team.doc.payment_mode == 'Card'
				"
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
		AlertAddPaymentMode: defineAsyncComponent(() =>
			import('../components/AlertAddPaymentMode.vue')
		),
		AlertCardExpired: defineAsyncComponent(() =>
			import('../components/AlertCardExpired.vue')
		),
		AlertAddressDetails: defineAsyncComponent(() =>
			import('../components/AlertAddressDetails.vue')
		),
		AlertMandateInfo: defineAsyncComponent(() =>
			import('../components/AlertMandateInfo.vue')
		)
	},
	props: {
		objectType: {
			type: String,
			required: true
		}
	},
	methods: {
		getRoute(row) {
			return {
				name: `${this.object.doctype} Detail`,
				params: {
					name: row.name
				}
			};
		}
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
		listOptions() {
			return {
				...this.object.list,
				doctype: this.object.doctype,
				route: this.object.detail ? this.getRoute : null
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
		banner() {
			return this.$resources.banner.doc;
		},
		isMandateNotSet() {
			return !this.$team.doc?.payment_method?.stripe_mandate_id;
		}
	},
	resources: {
		banner() {
			return {
				type: 'document',
				doctype: 'Dashboard Banner',
				name: 'Dashboard Banner'
			};
		}
	}
};
</script>
