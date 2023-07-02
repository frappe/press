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

		<div class="mt-3">
			<SectionHeader class="mb-2" heading="">
				<template #actions>
					<Input
						v-if="$resources.allBenches.data"
						type="select"
						:options="['Filter by Tag', ...$resources.allBenches.data.tags]"
						v-model="selectedTag"
						class="w-32"
					/>
				</template>
			</SectionHeader>
			<LoadingText v-if="$resources.allBenches.loading" />

			<BenchList v-else :benches="filteredBenches(benches)" />
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
			selectedTag: ''
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
		allBenches: 'press.api.bench.all'
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
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				this.$router.replace('/benches/new');
			}
		},
		filteredBenches(benches) {
			if (!this.selectedTag || this.selectedTag === 'Filter by Tag') {
				return benches;
			}

			return benches.filter(bench => bench.tags.includes(this.selectedTag));
		}
	}
};
</script>
