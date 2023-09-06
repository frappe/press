<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs :items="[{ label: 'Servers', route: { name: 'Servers' } }]">
				<template v-if="this.$account.team.enabled" #actions>
					<Dropdown
						v-if="
							$account.team.self_hosted_servers_enabled === 1 &&
							!showAddCardDialog
						"
						:options="dropDownOptions"
					>
						<Button
							variant="solid"
							iconLeft="plus"
							label="Create"
							class="ml-2 hidden sm:inline-flex"
						/>
					</Dropdown>
					<Button
						v-else
						variant="solid"
						iconLeft="plus"
						label="Create"
						class="ml-2 hidden sm:inline-flex"
						@click="showBillingDialog"
					/>
				</template>
			</Breadcrumbs>
		</header>

		<div>
			<div class="mx-5 mt-5">
				<div class="flex">
					<div class="flex w-full space-x-2 pb-4">
						<FormControl label="Search Servers" v-model="searchTerm">
							<template #prefix>
								<FeatherIcon name="search" class="w-4 text-gray-600" />
							</template>
						</FormControl>
						<FormControl
							label="Server Type"
							class="mr-8"
							type="select"
							:options="serverStatusFilterOptions()"
							v-model="server_type"
						/>
						<FormControl
							label="Tag"
							class="mr-8"
							type="select"
							:options="serverTagFilterOptions()"
							v-model="server_tag"
						/>
					</div>
				</div>
				<Table
					:columns="[
						{ label: 'Server Name', name: 'name', width: 2 },
						{ label: 'Status', name: 'status' },
						{ label: 'Region', name: 'region' },
						{ label: 'Tags', name: 'tags' },
						{ label: 'Plan', name: 'plan' },
						{ label: '', name: 'actions', width: 0.5 }
					]"
					:rows="servers"
					v-slot="{ rows, columns }"
				>
					<TableHeader class="hidden sm:grid" />
					<div class="flex items-center justify-center">
						<LoadingText class="mt-8" v-if="$resources.allServers.loading" />
						<div v-else-if="rows.length === 0" class="mt-8">
							<div class="text-base text-gray-700">No Items</div>
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
							<span v-else-if="column.name === 'plan'" class="hidden sm:block">
								{{
									row.plan
										? `${$planTitle(row.plan)}${
												row.plan.price_usd > 0 ? '/mo' : ''
										  }`
										: ''
								}}
							</span>
							<div v-else-if="column.name === 'region'" class="hidden sm:block">
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
								v-else-if="column.name == 'actions'"
								class="w-full text-right"
							>
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
							<span v-else>{{ row[column.name] || '' }}</span>
						</TableCell>
					</TableRow>
				</Table>
			</div>
		</div>
		<Dialog
			:options="{ title: 'Add card to create new servers' }"
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
	name: 'Servers',
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell,
		StripeCard: defineAsyncComponent(() =>
			import('@/components/StripeCard.vue')
		)
	},
	pageMeta() {
		return {
			title: 'Servers - Frappe Cloud'
		};
	},
	data() {
		return {
			showAddCardDialog: false,
			searchTerm: '',
			server_type: 'All Servers',
			server_tag: '',
			dropDownOptions: [
				{
					label: 'Frappe Cloud Server',
					onClick: () => this.$router.replace('/servers/new')
				},
				{
					label: 'Self Hosted Server',
					onClick: () => this.$router.replace('/selfhosted/new')
				}
			]
		};
	},
	resources: {
		allServers() {
			return {
				url: 'press.api.server.all',
				params: {
					server_filter: { server_type: this.server_type, tag: this.server_tag }
				},
				auto: true,
				onSuccess: data => {
					this.fuse = new Fuse(data, {
						keys: ['name', 'title', 'tags']
					});
				}
			};
		},
		serverTags: { url: 'press.api.server.server_tags', auto: true }
	},
	methods: {
		dropdownItems(server) {
			return [
				{
					label: 'Visit Server',
					onClick: () => {
						window.open(`https://${server.route.params.serverName}`, '_blank');
					}
				},
				{
					label: 'New Bench',
					onClick: () => {
						this.$router.push(`/servers/${server.app_server}/bench/new`);
					}
				}
			];
		},
		reload() {
			// refresh if currently not loading and have not reloaded in the last 5 seconds
			if (
				!this.$resources.allServers.loading &&
				new Date() - this.$resources.allServers.lastLoaded > 5000
			) {
				this.$resources.allServers.reload();
			}
		},
		showBillingDialog() {
			if (!this.$account.hasBillingInfo) {
				this.showAddCardDialog = true;
			} else {
				if (this.$account.team.self_hosted_servers_enabled !== 1) {
					this.$router.replace('/servers/new');
				}
				this.showAddCardDialog = false;
			}
		},
		serverStatusFilterOptions() {
			return [
				{
					label: 'All Servers',
					value: 'All Servers'
				},
				{
					label: 'App Servers',
					value: 'App Servers'
				},
				{
					label: 'Database Servers',
					value: 'Database Servers'
				}
			];
		},
		serverTagFilterOptions() {
			const defaultOptions = [
				{
					label: '',
					value: ''
				}
			];

			if (!this.$resources.serverTags.data) return defaultOptions;

			return [
				...defaultOptions,
				...this.$resources.serverTags.data.map(tag => ({
					label: tag,
					value: tag
				}))
			];
		}
	},
	computed: {
		servers() {
			if (!this.$resources.allServers.data) {
				return [];
			}

			let servers = this.$resources.allServers.data.filter(server =>
				this.$account.hasPermission(server.name, '', true)
			);

			if (this.searchTerm)
				servers = this.fuse.search(this.searchTerm).map(result => result.item);

			return servers.map(server => ({
				name: server.title || server.name,
				status: server.status,
				server_region_info: server.region_info,
				plan: server.plan,
				tags: server.tags,
				app_server: server.app_server,
				route: { name: 'ServerOverview', params: { serverName: server.name } }
			}));
		}
	}
};
</script>
