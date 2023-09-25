<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs
				:items="[{ label: 'Stacks', route: { name: 'StacksScreen' } }]"
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
					<FormControl label="Search Stacks" v-model="searchTerm">
						<template #prefix>
							<FeatherIcon name="search" class="w-4 text-gray-600" />
						</template>
					</FormControl>
					<FormControl
						label="Status"
						class="mr-8"
						type="select"
						:options="stackStatusFilterOptions()"
						v-model="stackFilter.status"
					/>
					<FormControl
						label="Tag"
						class="mr-8"
						type="select"
						:options="stackTagFilterOptions()"
						v-model="stackFilter.tag"
					/>
				</div>
				<div class="w-10"></div>
			</div>
			<Table
				:columns="[
					{ label: 'Stack Name', name: 'name', width: 2 },
					{ label: 'Status', name: 'status' },
					{ label: 'Tags', name: 'tags' },
					{ label: '', name: 'actions', width: 0.5 }
				]"
				:rows="stacks"
				v-slot="{ rows, columns }"
			>
				<TableHeader class="hidden sm:grid" />
				<div class="flex items-center justify-center">
					<LoadingText v-if="$resources.allStacks.loading" class="mt-8" />
					<div v-else-if="rows.length === 0" class="mt-8">
						<div class="text-base text-gray-700">No stacks</div>
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
								v-for="(tag, i) in row.tags?.slice(0, 1)"
								theme="blue"
								:label="tag"
							/>
							<Tooltip
								v-if="row.tags?.length > 1"
								:text="row.tags.slice(1).join(', ')"
							>
								<Badge
									v-if="row.tags?.length > 1"
									:label="`+${row.tags.length - 1}`"
								/>
							</Tooltip>
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
	name: 'StacksScreen',
	data() {
		return {
			showAddCardDialog: false,
			searchTerm: '',
			stackFilter: {
				status: 'All',
				tag: ''
			}
		};
	},
	pageMeta() {
		return {
			title: 'Stacks - Frappe Cloud'
		};
	},
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	resources: {
		allStacks() {
			return {
				url: 'press.api.stack.all',
				params: { stack_filter: this.stackFilter },
				auto: true,
				onSuccess: data => {
					this.fuse = new Fuse(data, {
						keys: ['title', 'tags']
					});
				}
			};
		},
		stackTags: {
			url: 'press.api.stack.stack_tags',
			auto: true
		}
	},
	computed: {
		stacks() {
			if (!this.$resources.allStacks.data) {
				return [];
			}
			let stacks = this.$resources.allStacks.data.filter(stack =>
				this.$account.hasPermission(stack.name, '', true)
			);
			if (this.searchTerm)
				stacks = this.fuse.search(this.searchTerm).map(result => result.item);

			return stacks.map(stack => ({
				name: stack.title,
				status: stack.status,
				tags: stack.tags,
				route: { name: 'StackServices', params: { stackName: stack.name } }
			}));
		}
	},
	methods: {
		stackStatusFilterOptions() {
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
		stackTagFilterOptions() {
			const defaultOptions = [
				{
					label: '',
					value: ''
				}
			];

			if (!this.$resources.stackTags.data) return defaultOptions;

			return [
				...defaultOptions,
				...this.$resources.stackTags.data.map(tag => ({
					label: tag,
					value: tag
				}))
			];
		},
		showBillingDialog() {
			this.$router.replace('/stacks/new');
		},
		dropdownItems(stack) {
			return [
				{
					label: 'View Sites',
					onClick: () => {
						this.$router.push({
							name: 'StackServices',
							params: { stackName: stack.route.params.stackName }
						});
					}
				}
			].filter(item => (item.condition ? item.condition() : true));
		}
	}
};
</script>
