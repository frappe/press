<template>
	<div class="fles">
		<div
			class="flex w-full justify-between space-x-2 pb-4 border-b bg-white px-5 py-2.5"
		>
			<header
				class="sticky top-0 z-10 flex items-center justify-between text-lg font-semibold"
			>
				Nginx Access Rule
			</header>
			<Button
				variant="outline"
				theme="gray"
				class="justify-end"
				appearance="primary"
				@click="showAddRuleDialog = true"
			>
				Add New Rule
			</Button>
		</div>
	</div>

	<div class="mx-5 mt-2">
		<div class="pb-20">
			<div class="flex">
				<div class="flex w-full space-x-2 pb-4">
					<FormControl v-model="searchTerm">
						<template #prefix>
							<FeatherIcon name="search" class="w-4 text-gray-600" />
						</template>
					</FormControl>
				</div>
			</div>
			<Table
				:columns="[
					{ label: 'IP Address', name: 'ip_address' },
					{ label: 'Rule', name: 'rule' },
					{ label: '', name: 'actions', width: 0.5 }
				]"
				:rows="nginxRules"
				v-slot="{ rows, columns }"
			>
				<TableHeader />
				<div class="flex items-center justify-center">
					<LoadingText class="mt-8" v-if="$resources.nginxRules.loading" />
					<div v-else-if="rows.length === 0" class="mt-8">
						<div class="text-base text-gray-700">No Data</div>
					</div>
				</div>

				<TableRow v-for="row in rows" :key="row.name" :row="row">
					<TableCell v-for="column in columns">
						<div
							v-if="column.name == 'actions' && !disableAction"
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
						<Badge
							v-else-if="column.name == 'rule'"
							:theme="getTheme(row)"
							:label="row[column.name]"
						/>
						<span v-else class="message">{{ row[column.name] || '' }}</span>
					</TableCell>
				</TableRow>
			</Table>
		</div>
	</div>

	<Dialog
		:options="{
			title: 'Add New Rule',
			actions: [
				{
					label: 'Add Rule',
					variant: 'solid',
					onClick: () => $resources.addRule.submit()
				}
			]
		}"
		v-model="showAddRuleDialog"
	>
		<template v-slot:body-content>
			<FormControl
				label="IP Address"
				class="mb-4"
				type="text"
				v-model="ipAddress"
				required
			/>
			<FormControl
				label="Action"
				type="select"
				:options="actions"
				v-model="action"
				required
			/>
		</template>
	</Dialog>
</template>

<script>
import Table from '@/components/Table/Table.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import TableCell from '@/components/Table/TableCell.vue';

export default {
	name: 'NginxAccessRule',
	props: ['server'],
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell
	},
	data() {
		return {
			showAddRuleDialog: false,
			ipAddress: '',
			actions: ['Allow', 'Deny'],
			action: 'Allow',
			rule: {
				ip_address: '',
				action: ''
			},
			searchTerm: ''
		};
	},
	resources: {
		nginxRules() {
			return {
				url: 'press.api.security.fetch_nginx_access_rules',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type
				},
				auto: true
			};
		},
		addRule() {
			return {
				url: 'press.api.security.add_nginx_access_rule',
				params: {
					server: this.server?.name,
					server_type: this.server?.server_type,
					ip_address: this.ipAddress,
					action: this.action
				},
				onSuccess() {
					this.showAddRuleDialog = false;
					this.$resources.nginxRules.fetch();
					notify({
						title: 'Rule Added',
						color: 'green',
						icon: 'check'
					});
				}
			};
		}
	},
	methods: {
		dropdownItems(group) {
			return [
				{
					label: 'Delete Rule',
					onClick: () => this.deleteGroup(group)
				}
			];
		},
		deleteGroup(group) {
			this.$resources.deleteGroup.submit({ name: group.name });
		},
		getTheme(rule) {
			return rule.rule === 'Allow' ? 'green' : 'red';
		}
	},
	computed: {
		nginxRules() {
			let nginxRules = [];

			nginxRules = this.$resources.nginxRules.data || [];

			if (this.searchTerm) {
				return nginxRules.filter(nginxRule =>
					nginxRule.ip_address
						.toLowerCase()
						.includes(this.searchTerm.toLowerCase())
				);
			}

			return nginxRules;
		}
	}
};
</script>
