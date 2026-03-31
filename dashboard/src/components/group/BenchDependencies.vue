<script setup lang="ts">
import { icon, renderDialog } from '@/utils/components';
import { createListResource, FeatherIcon, ListView, Tooltip } from 'frappe-ui';
import { computed, defineAsyncComponent, h } from 'vue';

defineOptions({ name: 'BenchDependencies' });

const props = defineProps({
	releaseGroup: {
		type: String,
	},
	releaseGroupDocumentResource: {
		type: Object,
	},
});

const dependencyListResource = createListResource({
	doctype: 'Release Group Dependency',
	fields: ['name', 'dependency', 'version'],
	filters: {
		parenttype: 'Release Group',
		parent: props.releaseGroup,
	},
	limit: 20,
	limit_page_length: 20,
	auto: true,
});

const columns = computed(() => [
	{
		label: 'Dependency',
		fieldname: 'dependency',
		format(_: any, row: any) {
			return row.title;
		},
	},
	{
		label: 'Version',
		fieldname: 'version',
		suffix(row: any) {
			if (!row.is_custom) {
				return;
			}

			return h('div', { title: 'Custom version' }, [
				h(icon('alert-circle', 'w-3 h-3')),
			]);
		},
		format(_: any, row: any) {
			return row.version;
		},
	},
	{
		label: '',
		key: '__actions',
		type: 'Actions',
		width: '100px',
		align: 'right',
		actions: (row: any) => [
			{
				label: 'Edit',
				onClick() {
					let DependencyEditorDialog = defineAsyncComponent(
						() => import('../../components/group/DependencyEditorDialog.vue'),
					);
					renderDialog(
						h(DependencyEditorDialog, {
							group: props.releaseGroupDocumentResource?.doc,
							dependency: row,
							onSuccess() {
								dependencyListResource.reload();
							},
						}),
					);
				},
			},
		],
	},
]);
</script>

<template>
	<div
		v-if="dependencyListResource"
		:key="dependencyListResource.list?.loading"
		class="text-right"
	>
		<Button
			label="Refresh"
			@click="dependencyListResource.reload()"
			:loading="dependencyListResource.list?.loading"
		>
			<template #icon>
				<Tooltip text="Refresh">
					<lucide-refresh-ccw class="h-4 w-4" />
				</Tooltip>
			</template>
		</Button>
	</div>

	<div class="mt-3 min-h-0 flex-1">
		<ListView
			:columns="columns"
			:rows="dependencyListResource.data ?? []"
			:options="{ emptyState: {}, selectable: false }"
			row-key="name"
		>
			<template #cell="{ item, row, column }">
				<ObjectListCell
					:class="[column == columns[0] ? ' text-gray-900' : ' text-gray-700']"
					:row="row"
					:column="column"
					:context="{
						listResource: dependencyListResource,
					}"
				/>
			</template>
		</ListView>

		<div class="px-5" v-if="!dependencyListResource.data?.length">
			<div
				class="text-center text-sm leading-10 text-gray-500 pb-[1.75rem]"
				v-if="dependencyListResource.list?.loading"
			>
				Loading...
			</div>
			<div
				v-else-if="dependencyListResource?.list?.error"
				class="py-4 text-center"
			>
				<ErrorMessage :message="dependencyListResource.list?.error" />
			</div>
			<div
				v-else
				class="text-center text-sm leading-10 text-gray-500 pb-[1.75rem]"
			>
				No dependencies to show
			</div>
		</div>

		<div
			class="p-2 text-right"
			:class="{
				'border-t bg-white bottom-0 sticky':
					dependencyListResource?.next && dependencyListResource?.hasNextPage,
			}"
			v-if="dependencyListResource"
		>
			<Button
				v-if="dependencyListResource.next && dependencyListResource.hasNextPage"
				@click="dependencyListResource.next()"
				:loading="dependencyListResource?.list?.loading"
			>
				Load more
			</Button>
		</div>

		<div
			class="text-ink-gray-5 select-none text-xs flex items-center w-full p-2 mb-3 rounded-md bg-gray-50"
		>
			<FeatherIcon name="info" class="size-4 inline-block mx-2" />
			<span>
				To include system package dependencies for your app, define them in your
				app's
				<code>pyproject.toml</code>. For more information, refer to the Frappe
				Cloud
				<a
					class="text-ink-blue-2"
					href="https://docs.frappe.io/cloud/faq/installing-app-apt-dependencies"
					target="_blank"
				>
					documentation</a
				>.
			</span>
		</div>
	</div>
</template>
