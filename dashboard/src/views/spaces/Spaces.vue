<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs :items="[{ label: 'Spaces', route: '/spaces' }]">
				<template v-if="this.$account.team.enabled" v-slot:actions>
					<Button
						variant="solid"
						iconLeft="plus"
						label="Create"
						class="ml-2"
						@click="showBillingDialog"
					/>
				</template>
			</Breadcrumbs>
		</header>

		<div class="mb-2" v-if="!$account.team.enabled">
			<Alert title="Your account is disabled">
				Enable your account to start creating spaces

				<template #actions>
					<Button variant="solid" route="/settings"> Enable Account </Button>
				</template>
			</Alert>
		</div>
		<div class="mx-5 mt-5">
			<div class="pb-20">
				<div class="flex">
					<div class="flex w-full space-x-2 pb-4">
						<FormControl label="Search Spaces" v-model="searchTerm">
							<template #prefix>
								<FeatherIcon name="search" class="w-4 text-gray-600" />
							</template>
						</FormControl>
						<FormControl
							label="Status"
							class="mr-8"
							type="select"
							:options="spaceStatusFilterOptions()"
							v-model="spaceFilter.status"
						/>
					</div>
				</div>
				<Table
					:columns="[
						{ label: 'Space Name', name: 'name', width: 2 },
						{ label: 'Status', name: 'status' },
						{ label: '', name: 'actions', width: 0.5 }
					]"
					:rows="servers"
					v-slot="{ rows, columns }"
				>
					<TableHeader />
					<div class="flex items-center justify-center">
						<LoadingText class="mt-8" v-if="$resources.spaces.loading" />
						<div v-else-if="rows.length === 0" class="mt-8">
							<div class="text-base text-gray-700">No Spaces</div>
						</div>
					</div>
					<TableRow v-for="row in rows" :key="row.name" :row="row">
						<TableCell v-for="column in columns">
							<Badge
								v-if="column.name === 'status'"
								:label="$siteStatus(row)"
							/>
							<span v-else-if="column.name === 'plan'">
								{{
									row.plan
										? `${$planTitle(row.plan)}${
												row.plan.price_usd > 0 ? '/mo' : ''
										  }`
										: ''
								}}
							</span>
							<div v-else-if="column.name === 'region'">
								<img
									v-if="row.server_region_info.image"
									class="h-4"
									:src="row.server_region_info.image"
									:alt="`Flag of ${row.server_region_info.title}`"
									:title="row.server_region_info.title"
								/>
								<span class="text-base text-gray-700" v-else>
									{{ row.server_region_info.title }}
								</span>
							</div>
							<div
								class="w-full text-right"
								v-else-if="column.name == 'actions'"
							>
								<Dropdown @click.prevent :options="dropdownItems(row)">
									<template v-slot="{ open }">
										<Button
											:variant="open ? 'subtle' : 'ghost'"
											icon="more-horizontal"
										/>
									</template>
								</Dropdown>
							</div>
							<span v-else>{{ row[column.name] || '' }}</span>
						</TableCell>
					</TableRow>
				</Table>
			</div>
		</div>
	</div>
</template>

<script>
import Table from '@/components/Table/Table.vue';
import TableCell from '@/components/Table/TableCell.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import SpacesList from './SpacesList.vue';
import CodeServersList from './CodeServersList.vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';

export default {
	name: 'Spaces',
	components: {
		SpacesList,
		CodeServersList,
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	data() {
		return {
			searchTerm: '',
			spaceFilter: {
				status: 'All'
			}
		};
	},
	resources: {
		spaces() {
			return {
				method: 'press.api.spaces.spaces',
				auto: true,
				params: { space_filter: this.spaceFilter },
				onSuccess: data => {
					this.fuse = new Fuse(data['servers'], {
						keys: ['name']
					});
				}
			};
		}
	},
	methods: {
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				this.$router.replace('/codeservers/new');
			}
		},
		spaceStatusFilterOptions() {
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
					label: 'Broken',
					value: 'Broken'
				}
			];
		},
		dropdownItems(space) {
			return [
				{
					label: 'Open',
					onClick: () => {
						window.open(`https://${space.name}`, '_blank');
					}
				}
			];
		}
	},
	computed: {
		servers() {
			if (!this.$resources.spaces.data) {
				return [];
			}
			if (this.searchTerm) {
				return this.fuse.search(this.searchTerm).map(result => result.item);
			}

			return this.$resources.spaces.data.servers.map(server => ({
				name: server.name,
				status: server.status,
				route: `/codeservers/${server.name}/overview`
			}));
		}
	}
};
</script>
