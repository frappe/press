<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<BreadCrumbs
				:items="[{ label: 'Benches', route: { name: 'BenchesScreen' } }]"
			>
				<template v-slot:actions>
					<Button
						variant="solid"
						icon-left="plus"
						label="Create"
						class="ml-2"
						@click="showBillingDialog"
					/>
				</template>
			</BreadCrumbs>
		</header>

		<div class="mx-5 mt-5">
			<div class="flex">
				<div class="flex w-full space-x-2 pb-4">
					<FormControl label="Search Benches" v-model="searchTerm">
						<template #prefix>
							<FeatherIcon name="search" class="w-4 text-gray-600" />
						</template>
					</FormControl>
					<FormControl
						label="Status"
						class="mr-8"
						type="select"
						:options="benchStatusFilterOptions()"
						v-model="benchFilter.status"
					/>
					<FormControl
						label="Tag"
						class="mr-8"
						type="select"
						:options="benchTagFilterOptions()"
						v-model="benchFilter.tag"
					/>
				</div>
				<div class="w-10"></div>
			</div>
			<LoadingText v-if="$resources.allBenches.loading" />
			<div v-else>
				<div class="flex">
					<div class="flex w-full px-3 py-4">
						<div class="w-4/12 text-base font-medium text-gray-900">
							Bench Name
						</div>
						<div class="w-2/12 text-base font-medium text-gray-900">Status</div>
						<div class="w-2/12 text-base font-medium text-gray-900">
							Version
						</div>
						<div class="w-2/12 text-base font-medium text-gray-900">Tags</div>
						<div class="w-2/12 text-base font-medium text-gray-900">Stats</div>
					</div>
					<div class="w-10" />
				</div>
				<div class="mx-2.5 border-b" />
				<ListView :items="benches" :dropdownItems="dropdownItems" />
			</div>
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
import ListView from '@/components/ListView.vue';
import { defineAsyncComponent } from 'vue';
import { FormControl } from 'frappe-ui';

export default {
	name: 'BenchesScreen',
	data() {
		return {
			showAddCardDialog: false,
			searchTerm: '',
			benchFilter: {
				status: 'All',
				tag: ''
			}
		};
	},
	pageMeta() {
		return {
			title: 'Benches - Frappe Cloud'
		};
	},
	components: {
		ListView,
		FormControl,
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		)
	},
	resources: {
		paymentMethods: 'press.api.billing.get_payment_methods',
		allBenches() {
			return {
				method: 'press.api.bench.all',
				params: { bench_filter: this.benchFilter },
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
			let benches = this.$resources.allBenches.data;
			if (this.searchTerm)
				benches = benches.filter(bench =>
					bench.name.toLowerCase().includes(this.searchTerm.toLowerCase())
				);

			return benches.map(bench => ({
				name: bench.title,
				status: bench.status,
				version: bench.version,
				number_of_sites: bench.number_of_sites,
				number_of_apps: bench.number_of_apps,
				tags: bench.tags,
				link: { name: 'BenchOverview', params: { benchName: bench.name } }
			}));
		}
	},
	methods: {
		benchStatusFilterOptions() {
			return [
				{
					label: 'All',
					value: 'All'
				},
				{
					label: 'Active',
					value: 'Active'
				},
				{
					label: 'Awaiting Deploy',
					value: 'Awaiting Deploy'
				}
			];
		},
		benchTagFilterOptions() {
			const defaultOptions = [
				{
					label: '',
					value: ''
				}
			];

			if (!this.$resources.benchTags.data) return defaultOptions;

			return [
				...defaultOptions,
				...this.$resources.benchTags.data.map(tag => ({
					label: tag,
					value: tag
				}))
			];
		},
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				this.$router.replace('/benches/new');
			}
		},
		dropdownItems(bench) {
			return [
				{
					label: 'New Site',
					onClick: () => {
						this.$router.push(`/${bench.name}/new`);
					}
				},
				{
					label: 'View Versions',
					onClick: () => {
						this.$router.push(`/benches/${bench.name}/versions`);
					}
				}
			];
		}
	}
};
</script>
