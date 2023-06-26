<template>
	<div>
		<PageHeader title="Benches" subtitle="Private benches you own">
			<template v-slot:actions>
				<Button
					appearance="primary"
					iconLeft="plus"
					class="ml-2"
					@click="showBillingDialog"
				>
					New
				</Button>
			</template>
		</PageHeader>

		<SectionHeader
			:heading="
				benchStatus === 'Awaiting Deploy'
					? 'Benches Awaiting Deploy'
					: `${this.benchStatus || 'All'} Benches`
			"
		>
			<template #actions>
				<Input
					type="select"
					:options="benchStatusOptions"
					v-model="benchStatus"
					@change="
						pageStart = 0;
						$resources.allBenches.reset();
					"
				/>
			</template>
		</SectionHeader>

		<div class="mt-3">
			<LoadingText v-if="$resources.allBenches.loading && pageStart === 0" />
			<BenchList v-else :benches="benches" />
		</div>
		<div
			class="py-3"
			v-if="!$resources.allBenches.lastPageEmpty && benches.length > 0"
		>
			<Button
				:loading="$resources.allBenches.loading"
				loadingText="Loading..."
				@click="pageStart += 10"
			>
				Load more
			</Button>
		</div>

		<Dialog
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
		</Dialog>
	</div>
</template>

<script>
import BenchList from './BenchList.vue';
import { defineAsyncComponent } from 'vue';

export default {
	name: 'BenchesScreen',
	data() {
		return {
			benchStatusOptions: [
				{
					label: 'All',
					value: ''
				},
				{
					label: 'Active',
					value: 'Active'
				},
				{
					label: 'Awaiting Deploy',
					value: 'Awaiting Deploy'
				}
			],
			showAddCardDialog: false,
			benchStatus: '',
			pageStart: 0
		};
	},
	pageMeta() {
		return {
			title: 'Benches - Frappe Cloud'
		};
	},
	components: {
		BenchList,
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		)
	},
	resources: {
		paymentMethods: 'press.api.billing.get_payment_methods',
		allBenches() {
			return {
				method: 'press.api.bench.all',
				params: { start: this.pageStart, status: this.benchStatus },
				pageLength: this.pageLength(),
				keepData: true,
				auto: true
			};
		}
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
		pageLength() {
			return this.pageStart === 0 ? 0 : 10;
		},
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				this.$router.replace('/benches/new');
			}
		}
	}
};
</script>
