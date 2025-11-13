<template>
	<Dialog
		:options="{
			title: 'App Versions',
			size: '2xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="$resources?.showAppVersions?.loading"
				class="flex h-80 w-full items-center justify-center gap-2 text-base text-gray-700"
			>
				<Spinner class="w-4" /> Fetching app versions ...
			</div>
			<div
				v-else-if="$resources?.showAppVersions?.error"
				class="flex h-80 w-full items-center justify-center text-red-600"
			>
				Failed to fetch app versions
			</div>
			<ListView
				v-else
				class="h-80"
				:columns="columns"
				:rows="formattedRows"
				:options="{
					resizeColumn: true,
					selectable: false,
					onRowClick: handleRowClick,
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
					<ListRow v-for="(row, i) in formattedRows" :row="row" :key="row.name">
						<template v-slot="{ column, item }">
							<div class="truncate text-base" :class="column.class">
								<template v-if="column.class === 'font-mono'">
									<Badge :label="item" />
								</template>

								<template v-else>
									{{ item }}
								</template>
							</div>
						</template>
					</ListRow>
				</ListRows>
			</ListView>
			<Button
				v-if="
					!['Draft', 'Preparing', 'Running', 'Pending'].includes(status) &&
					!$resources?.redeployBuild?.loading
				"
				variant="solid"
				iconLeft=""
				theme="gray"
				@click="onRedeploy()"
				class="mt-4 w-full rounded"
			>
				Redeploy
			</Button>
		</template>
	</Dialog>
</template>

<script>
import {
	ListHeader,
	ListHeaderItem,
	ListRow,
	ListRows,
	ListView,
	Spinner,
} from 'frappe-ui';
import { toast } from 'vue-sonner';
export default {
	name: 'AppVersionsDialog',
	props: ['group', 'dc_name', 'status'],
	components: {
		Spinner,
		ListView,
		ListHeader,
		ListHeaderItem,
		ListRows,
		ListRow,
	},
	data() {
		return {
			show: true,
		};
	},
	computed: {
		formattedRows() {
			return (
				this.$resources?.showAppVersions?.data?.map((item) => ({
					...item,
					repository: `${item.repository_owner}/${item.repository}`,
				})) || []
			);
		},
		columns() {
			return [
				{
					label: 'App',
					key: 'name',
					width: 2,
				},
				{
					label: 'Commit',
					key: 'hash',
					width: 2,
					class: 'font-mono',
				},
				{
					label: 'Branch',
					key: 'branch',
					width: 2,
				},
				{
					label: 'Repository',
					key: 'repository',
					width: 2,
				},
			];
		},
	},
	resources: {
		showAppVersions() {
			return {
				url: 'press.api.bench.show_app_versions',
				makeParams: () => {
					return {
						name: this.group,
						dc_name: this.dc_name,
					};
				},
				auto: true,
			};
		},
		redeployBuild() {
			return {
				url: 'press.api.bench.redeploy',
				makeParams: () => {
					return {
						name: this.group,
						dc_name: this.dc_name,
					};
				},
				auto: false,
			};
		},
	},
	methods: {
		async onRedeploy() {
			await this.$resources.redeployBuild
				.submit()
				.then((response) => {
					this.$router.push({
						path: response,
					});
					this.show = false;
				})
				.catch(() => {
					toast.error('Failed to redeploy');
				});
		},
		handleRowClick(row) {
			window.open(`${row.repository_url}/commits/${row.hash}`, '_blank');
		},
	},
};
</script>
