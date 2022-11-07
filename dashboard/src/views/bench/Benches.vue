<template>
	<div>
		<PageHeader title="Benches" subtitle="Private benches you own">
			<template v-slot:actions>
				<Button
					appearance="primary"
					iconLeft="plus"
					class="ml-2 hidden sm:inline-flex"
					@click="showBillingDialog"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<div>
			<SectionHeader heading="All Benches">
				<template v-slot:actions>
					<SiteAndBenchSearch />
				</template>
			</SectionHeader>

			<div class="mt-3">
				<LoadingText v-if="$resources.allBenches.loading" />
				<BenchList v-else :benches="benches" />
			</div>
		</div>

		<FrappeUIDialog
			:options="{ title: 'Add card to create new benches' }"
			v-model="showAddCardDialog"
		>
			<template v-slot:body-content>
				<StripeCard
					class="mb-1"
					v-if="showAddCardDialog"
					@complete="
						showAddCardDialog = false;
						$resources.paymentMethods.reload();
					"
				/>
			</template>
		</FrappeUIDialog>
	</div>
</template>

<script>
import SiteAndBenchSearch from '@/components/SiteAndBenchSearch.vue';
import BenchList from './BenchList.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'BenchesScreen',
	data() {
		return {
			showAddCardDialog: false
		}
	},
	pageMeta() {
		return {
			title: 'Benches - Frappe Cloud'
		};
	},
	components: { 
		SiteAndBenchSearch, 
		BenchList,
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		)
	},
	resources: {
		paymentMethods: 'press.api.billing.get_payment_methods',
		allBenches: 'press.api.bench.all'
	},
	computed: {
		benches() {
			if (!this.$resources.allBenches.data) {
				return [];
			}

			return this.$resources.allBenches.data;
		}
	},
	methods: {
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				window.location.href = `/dashboard/benches/new`;
			}
		}
	}
};
</script>
