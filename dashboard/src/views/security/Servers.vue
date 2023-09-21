<template>
	<div>
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-5 py-2.5"
		>
			<Breadcrumbs :items="[{ label: 'Security', route: '/security' }]">
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
							:options="serverTypeFilterOptions()"
							v-model="server_type"
						/>
					</div>
				</div>
				<Table
					:columns="[
						{ label: 'Server Name', name: 'name' },
						{ label: 'Security Updates', name: 'security_updates_status' },
						{ label: '', name: 'actions', width: 0.5 }
					]"
					:rows="servers"
					v-slot="{ rows, columns }"
				>
					<TableHeader class="hidden sm:grid" />
					<TableRow v-for="row in rows" :key="row.name" :row="row">
						<TableCell v-for="column in columns">
							<Badge
								v-if="column.name === 'security_updates_status'"
								:label="row[column.name]"
								:theme="row[column.name] === 'Up to date' ? 'green' : 'red'"
							/>
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
							<span v-else>
								{{ row[column.name] || '' }}
							</span>
						</TableCell>
					</TableRow>
					<div class="mt-8 flex items-center justify-center">
						<LoadingText
							v-if="
								$resources.allServers.loading && !$resources.allServers.data
							"
						/>
						<div
							v-else-if="$resources.allServers.fetched && rows.length === 0"
							class="text-base text-gray-700"
						>
							No Servers
						</div>
					</div>
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
import Fuse from 'fuse.js/dist/fuse.basic.esm';

export default {
	name: 'Servers',
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	pageMeta() {
		return {
			title: 'Security - Frappe Cloud'
		};
	},
	data() {
		return {
			searchTerm: '',
			server_type: 'All Servers'
		};
	},
	resources: {
		allServers() {
			return {
				url: 'press.api.security.get_servers',
				params: {
					server_filter: { server_type: this.server_type, tag: '' }
				},
				auto: true,
				cache: [
					'SecurityServerList',
					this.server_type,
					this.$account.team.name
				],
				onSuccess: data => {
					this.fuse = new Fuse(data, {
						keys: ['name', 'title']
					});
				}
			};
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
				...server,
				name: server.title || server.name,
				route: { name: 'SecurityOverview', params: { serverName: server.name } }
			}));
		}
	},
	methods: {
		getServerFilterHeading() {
			return this.serverFilter;
		},
		serverFilterOptions() {
			const options = [
				{
					group: 'Types',
					items: [
						{
							label: 'All Servers',
							onClick: () => (this.serverFilter = 'All Servers')
						},
						{
							label: 'App Servers',
							onClick: () => (this.serverFilter = 'App Servers')
						},
						{
							label: 'Database Servers',
							onClick: () => (this.serverFilter = 'Database Servers')
						}
					]
				}
			];

			return options;
		},
		serverTypeFilterOptions() {
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
		dropdownItems(server) {
			return [
				{
					label: 'View Security Updates',
					onClick: () => {
						this.$router.push(
							`/security/${server.route.params.serverName}/security_update`
						);
					}
				},
				{
					label: 'Manage Firewall',
					onClick: () => {
						this.$router.push(`/security/${server.app_server}/firewall`);
					}
				},
				{
					label: 'SSH Sessions',
					onClick: () => {
						this.$router.push(`/security/${server.app_server}/ssh_session_log`);
					}
				}
			];
		}
	}
};
</script>
