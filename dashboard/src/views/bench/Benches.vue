<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs
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
			</Breadcrumbs>
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
			<Table
				:columns="[
					{ label: 'Bench Name', name: 'name', width: 2 },
					{ label: 'Status', name: 'status' },
					{ label: 'Version', name: 'version' },
					{ label: 'Tags', name: 'tags' },
					{ label: 'Stats', name: 'stats' },
					{ label: '', name: 'actions', width: 0.5 }
				]"
				:rows="benches"
				v-slot="{ rows, columns }"
			>
				<TableHeader class="hidden sm:grid" />
				<div class="flex items-center justify-center">
					<LoadingText v-if="$resources.allBenches.loading" class="mt-8" />
					<div v-else-if="rows.length === 0" class="mt-8">
						<div class="text-base text-gray-700">No benches</div>
					</div>
				</div>
				<TableRow v-for="row in rows" :key="row.name" :row="row">
					<TableCell v-for="column in columns">
						<Badge v-if="column.name === 'status'" :label="row.status" />
						<div
							v-else-if="column.name === 'tags'"
							class="hidden space-x-1 sm:flex"
						>
							<Badge
								v-for="(tag, i) in row.tags.slice(0, 1)"
								theme="blue"
								:label="tag"
							/>
							<Tooltip
								v-if="row.tags.length > 1"
								:text="row.tags.slice(1).join(', ')"
							>
								<Badge
									v-if="row.tags.length > 1"
									:label="`+${row.tags.length - 1}`"
								/>
							</Tooltip>
						</div>
						<div
							v-else-if="column.name === 'stats'"
							class="hidden text-sm text-gray-600 sm:block"
						>
							{{
								`${row.stats.number_of_sites} ${$plural(
									row.stats.number_of_sites,
									'Site',
									'Sites'
								)}`
							}}
							&middot;
							{{
								`${row.stats.number_of_apps} ${$plural(
									row.stats.number_of_apps,
									'App',
									'Apps'
								)}`
							}}
						</div>
						<div v-else-if="column.name == 'actions'" class="w-full text-right">
							<Dropdown @click.prevent :options="dropdownItems(row)">
								<template v-slot="{ open }">
									<Button
										:variant="open ? 'subtle' : 'ghost'"
										class="mr-2"
										icon="more-horizontal"
									/>
								</template>
							</Dropdown>
						</div>
						<span
							v-else
							:class="{ 'hidden sm:block': column.name === 'version' }"
							>{{ row[column.name] || '' }}
						</span>
					</TableCell>
				</TableRow>
			</Table>
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
import Table from '@/components/Table/Table.vue';
import TableCell from '@/components/Table/TableCell.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import { defineAsyncComponent } from 'vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';

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
		Table,
		TableHeader,
		TableRow,
		TableCell,
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
				auto: true,
				onSuccess: data => {
					this.fuse = new Fuse(data, {
						keys: ['title', 'tags']
					});
				}
			};
		},
		benchTags: 'press.api.bench.bench_tags'
	},
	computed: {
		benches() {
			if (!this.$resources.allBenches.data) {
				return [];
			}
			let benches = this.$resources.allBenches.data.filter(bench =>
				this.$account.hasPermission(bench.name, '', true)
			);
			if (this.searchTerm)
				benches = this.fuse.search(this.searchTerm).map(result => result.item);

			return benches.map(bench => ({
				name: bench.title,
				status: bench.status,
				version: bench.version,
				stats: {
					number_of_sites: bench.number_of_sites,
					number_of_apps: bench.number_of_apps
				},
				tags: bench.tags,
				route: { name: 'BenchSiteList', params: { benchName: bench.name } }
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
						this.$router.push({
							name: 'NewBenchSite',
							params: { bench: bench.route.params.benchName }
						});
					},
					condition: () => bench.status === 'Active'
				},
				{
					label: 'View Sites',
					onClick: () => {
						this.$router.push({
							name: 'BenchSiteList',
							params: { benchName: bench.route.params.benchName }
						});
					}
				}
			].filter(item => (item.condition ? item.condition() : true));
		}
	}
};
</script>
