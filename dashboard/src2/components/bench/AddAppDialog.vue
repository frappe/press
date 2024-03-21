<template>
	<Dialog
		:options="{
			title: 'Add Marketplace App',
			size: '6xl'
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<div class="flex">
				<div>
					<TextInput
						placeholder="Search"
						class="w-[20rem]"
						:debounce="500"
						v-model="searchQuery"
					>
						<template #prefix>
							<i-lucide-search class="h-4 w-4 text-gray-500" />
						</template>
						<template #suffix>
							<span class="text-sm text-gray-500" v-if="searchQuery">
								{{
									filteredRows.length === 0
										? 'No results'
										: `${filteredRows.length} of ${rows.length}`
								}}
							</span>
						</template>
					</TextInput>
				</div>
				<div class="ml-auto flex items-center space-x-2">
					<Button
						@click="$resources.installableApps.reload()"
						:loading="isLoading"
					>
						<template #icon>
							<i-lucide-refresh-ccw class="h-4 w-4" />
						</template>
					</Button>
					<Button
						@click="
							showDialog = false;
							showNewAppDialog = true;
						"
					>
						<template #prefix>
							<i-lucide-github class="h-4 w-4" />
							Add from GitHub
						</template>
					</Button>
				</div>
			</div>
			<div class="mt-3 min-h-0 flex-1 overflow-y-auto">
				<ListView
					:columns="columns"
					:rows="filteredRows"
					:options="{
						selectable: false,
						onRowClick: () => {},
						getRowRoute: null
					}"
					row-key="name"
				>
					<ListHeader>
						<ListHeaderItem
							v-for="column in columns"
							:key="column.key"
							:item="column"
						/>
					</ListHeader>
					<ListRows>
						<ListRow
							v-for="(row, i) in filteredRows"
							:row="row"
							:key="row.name"
						>
							<template v-slot="{ column, item }">
								<div class="flex items-center">
									<div v-if="column.prefix" class="mr-2">
										<component :is="column.prefix(row)" />
									</div>
									<Dropdown
										:options="dropdownItems(row)"
										right
										v-if="column.type === 'select'"
									>
										<template v-slot="{ open }">
											<Button
												v-if="row.source.branch"
												type="white"
												icon-right="chevron-down"
											>
												<span>{{ row.source.branch }}</span>
											</Button>
										</template>
									</Dropdown>
									<Button
										v-else-if="column.type === 'Button'"
										label="Add"
										@click="addApp(row)"
										:icon-left="addedApps.includes(row) ? 'check' : 'plus'"
										:disabled="!row.compatible"
										:class="{
											'pointer-events-none': addedApps.includes(row)
										}"
									/>
									<Badge
										v-else-if="column.type === 'Badge'"
										v-bind="formattedValue(column, item, row)"
									/>
									<div v-else class="truncate text-base" :class="column.class">
										{{ formattedValue(column, item, row) }}
									</div>
								</div>
							</template>
						</ListRow>
					</ListRows>
				</ListView>
				<div class="px-5" v-if="filteredRows.length === 0">
					<div
						class="text-center text-sm leading-10 text-gray-500"
						v-if="isLoading"
					>
						Loading...
					</div>
					<div v-else class="text-center text-sm leading-10 text-gray-500">
						No apps available to add
					</div>
				</div>
			</div>
		</template>
	</Dialog>
	<NewAppDialog v-if="showNewAppDialog" @app-added="addAppFromGithub" />
</template>

<script>
import {
	ListView,
	ListHeader,
	ListHeaderItem,
	ListRow,
	ListRows,
	ListRowItem,
	TextInput
} from 'frappe-ui';
import { toast } from 'vue-sonner';
import { h } from 'vue';
import NewAppDialog from '../NewAppDialog.vue';

export default {
	name: 'AddAppDialog',
	props: ['groupName', 'groupVersion'],
	components: {
		ListView,
		ListHeader,
		ListHeaderItem,
		ListRow,
		ListRows,
		ListRowItem,
		TextInput,
		NewAppDialog
	},
	emits: ['appAdd', 'new-app'],
	data() {
		return {
			searchQuery: '',
			showNewAppDialog: false,
			selectedAppSources: [],
			selectedBranch: '',
			showDialog: true,
			addedApps: [],
			columns: [
				{
					label: 'Title',
					key: 'title',
					class: 'font-medium',
					prefix(row) {
						return row.image
							? h('img', {
									src: row.image,
									class: 'w-6 h-6 rounded',
									alt: row.title
							  })
							: h(
									'div',
									{
										class:
											'w-6 h-6 rounded bg-gray-300 text-gray-600 flex items-center justify-center'
									},
									row.title[0].toUpperCase()
							  );
					}
				},
				{
					label: 'Repository',
					key: 'repo',
					class: 'text-gray-600'
				},
				{
					label: 'Branch',
					type: 'select',
					key: 'sources',
					format(value, row) {
						return row.sources.map(s => {
							return {
								label: s.branch,
								value: s.name
							};
						});
					}
				},
				{
					label: '',
					key: 'compatible',
					type: 'Badge',
					format(value) {
						return {
							label: value ? 'Compatible' : 'Incompatible',
							theme: value ? 'green' : 'red'
						};
					}
				},
				{
					label: '',
					type: 'Button',
					width: '5rem'
				}
			]
		};
	},
	resources: {
		addApp: {
			url: 'press.api.bench.add_app',
			onSuccess() {
				this.$emit('appAdd');
			},
			onError(e) {
				toast.error(e.messages.length ? e.messages.join('\n') : e.message);
			}
		},
		installableApps() {
			return {
				url: 'press.api.bench.all_apps',
				params: {
					name: this.groupName
				},
				transform(data) {
					return data.map(app => {
						app.compatible = app.sources.length > 0;
						app.source = app.sources.length > 0 ? app.sources[0] : {};
						return app;
					});
				},
				auto: true,
				initialData: []
			};
		}
	},
	computed: {
		rows() {
			return this.$resources.installableApps.data;
		},
		filteredRows() {
			if (!this.searchQuery) return this.rows;
			let query = this.searchQuery.toLowerCase();

			return this.rows.filter(row => {
				let values = this.columns.map(column => {
					let value = row[column.key];
					if (column.format) {
						value = column.format(value, row);
					}
					return value;
				});
				for (let value of values) {
					if (value && value.toLowerCase?.().includes(query)) {
						return true;
					}
				}
				return false;
			});
		},
		isLoading() {
			return (
				this.$resources.addApp.loading ||
				this.$resources.installableApps.loading
			);
		}
	},
	methods: {
		addAppFromGithub(app) {
			app.group = this.groupName;
			this.$emit('new-app', app);
		},
		addApp(row) {
			if (!this.selectedAppSources.includes(row))
				this.selectedAppSources.push(row);

			let app = this.selectedAppSources.find(app => app.name === row.name);

			this.$resources.addApp
				.submit({
					name: this.groupName,
					source: app.source.name,
					app: app.name
				})
				.then(() => {
					this.addedApps.push(app);
				});
		},
		dropdownItems(row) {
			return row.sources.map(source => ({
				label: `${source.repository_owner}/${source.repository}:${source.branch}`,
				onClick: () => this.selectSource(row, source)
			}));
		},
		selectSource(app, source) {
			app.source = source;
			this.selectedAppSources = this.filteredRows.map(_app => {
				if (app.name === _app.app) {
					return {
						app: app.name,
						source
					};
				}
				return _app;
			});
		},
		formattedValue(column, value, row) {
			let formattedValue = column.format ? column.format(value, row) : value;
			if (formattedValue == null) {
				formattedValue = '';
			}
			return typeof formattedValue === 'object'
				? formattedValue
				: String(formattedValue);
		}
	}
};
</script>
