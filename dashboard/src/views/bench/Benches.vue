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

		<SectionHeader :heading="getBenchFilterHeading()">
			<template #actions>
				<select
					v-model="benchFilter"
					class="form-select"
					@change="handleChange"
				>
					<optgroup v-for="group in benchFilterOptions" :label="group.group">
						<option
							v-for="option in group.items"
							:key="option.value"
							:value="option.value"
							:selected="benchFilter === option.value"
						>
							{{ option.label }}
						</option>
					</optgroup>
				</select>
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
			showAddCardDialog: false,
			benchFilter: '',
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
				params: { start: this.pageStart, bench_filter: this.benchFilter },
				pageLength: 10,
				keepData: true,
				auto: true
			};
		},
		benchTags: 'press.api.bench.bench_tags'
	},
	computed: {
		benches() {
			if (!this.$resources.allBenches.data) {
				return [];
			}

			return this.$resources.allBenches.data;
		},
		benchFilterOptions() {
			const options = [
				{
					group: 'Status',
					items: [
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
					]
				}
			];
			if (!this.$resources.benchTags?.data) return options;

			return [
				...options,
				{
					group: 'Tags',
					items: this.$resources.benchTags.data.map(tag => ({
						label: tag,
						value: `tag:${tag}`
					}))
				}
			];
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
		getBenchFilterHeading() {
			if (this.benchFilter === 'Awaiting Deploy')
				return 'Benches Awaiting Deploy';
			else if (this.benchFilter.startsWith('tag:'))
				return `Benches with tag ${this.benchFilter.slice(4)}`;
			return `${this.benchFilter || 'All'} Benches`;
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
