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
				benchFilter === 'Awaiting Deploy'
					? 'Benches Awaiting Deploy'
					: `${this.benchFilter || 'All'} Benches`
			"
		>
			<template #actions>
				<Input
					v-if="$resources.allBenches.data"
					type="select"
					:options="[...benchStatusOptions, ...$resources.allBenches.data.tags.map(tag => ({ label: tag, value: `tag:${tag}` }))]"
					v-model="benchFilter"
					@change="handleChange"
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
				// TODO: rewrite this to use the tags from the API
			],
			showAddCardDialog: false,
			benchFilter: '',
			pageStart: 0,
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
				params: { start: this.pageStart, bench_filter: this.benchFilter },
				pageLength: 10,
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

			return this.$resources.allBenches.data.groups;
		}
	},
	methods: {
		handleChange() {
			// wrapping in a timeout to avoid a bug where the previous filter's data is fetched again
			setTimeout(() => {
				this.pageStart = 0;
				this.$resources.allBenches.reset();
			}, 1);
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
