<template>
	<div class="mb-5 flex items-center gap-2">
		<Tooltip text="All Roles">
			<Button :route="{ name: 'SettingsPermissionRoles' }">
				<template #icon>
					<i-lucide-arrow-left class="h-4 w-4 text-gray-700" />
				</template>
			</Button>
		</Tooltip>
		<h3 class="text-lg font-medium text-gray-900">
			{{ role.doc?.title }}
		</h3>
		<Tooltip text="Admin Role" v-if="role.doc?.admin_access">
			<FeatherIcon name="shield" class="h-5 w-5 text-gray-700" />
		</Tooltip>
	</div>
	<ObjectList
		:options="rolePermissions"
		@update:selections="(e) => (selectedItems = e)"
	>
		<template #header-left="{ listResource }">
			<Dropdown :options="getDropdownOptions(listResource)">
				<Button>
					<template #prefix>
						<LucideAppWindow class="h-4 w-4 text-gray-500" />
					</template>
					{{ currentDropdownOption.label }}
					<template #suffix>
						<FeatherIcon name="chevron-down" class="h-4 w-4 text-gray-500" />
					</template>
				</Button>
			</Dropdown>
		</template>
	</ObjectList>
</template>

<script setup>
import {
	Button,
	Dropdown,
	createDocumentResource,
	createResource,
} from 'frappe-ui';
import { computed, h, ref } from 'vue';
import LucideAppWindow from '~icons/lucide/app-window';
import ObjectList from '../ObjectList.vue';
import { toast } from 'vue-sonner';
import { getToastErrorMessage } from '../../utils/toast';
import { confirmDialog, icon, renderDialog } from '../../utils/components';
import RoleConfigureDialog from './RoleConfigureDialog.vue';

let selectedItems = ref(new Set());

const props = defineProps({
	roleId: { type: String, required: true },
});

const role = createDocumentResource({
	doctype: 'Press Role',
	name: props.roleId,
	auto: true,
	whitelistedMethods: {
		addUser: 'add_user',
		removeUser: 'remove_user',
		bulkDelete: 'delete_permissions',
	},
});

const docInsert = createResource({
	url: 'press.api.client.insert',
});

const dropdownOptions = [
	{ label: 'Allowed Sites', doctype: 'Site', fieldname: 'site' },
	{
		label: 'Allowed Bench Groups',
		doctype: 'Release Group',
		fieldname: 'release_group',
	},
	{ label: 'Allowed Servers', doctype: 'Server', fieldname: 'server' },
];
const currentDropdownOption = ref(dropdownOptions[0]);
function getDropdownOptions(listResource) {
	return dropdownOptions.map((option) => {
		return {
			...option,
			onClick: () => {
				currentDropdownOption.value = option;
				let filters = {
					role: props.roleId,
				};
				if (option.doctype === 'Site') {
					filters.site = ['is', 'set'];
				}
				if (option.doctype === 'Release Group') {
					filters.release_group = ['is', 'set'];
				}
				if (option.doctype === 'Server') {
					filters.server = ['is', 'set'];
				}
				listResource.update({ filters });
				listResource.reload();
			},
		};
	});
}

const rolePermissions = ref({
	doctype: 'Press Role Permission',
	fields: [
		'site',
		'site.host_name as site_host_name',
		'release_group',
		'release_group.title as release_group_title',
		'server',
		'server.title as server_title',
	],
	filters: {
		role: props.roleId,
		site: ['is', 'set'],
	},
	selectable: true,
	columns: [
		{
			label: computed(() =>
				currentDropdownOption.value.doctype.replace(
					'Release Group',
					'Bench Group',
				),
			),
			format(_value, row) {
				return (
					row.site_host_name ||
					row.site ||
					row.release_group_title ||
					row.server_title
				);
			},
		},
	],
	actions({ listResource: permissions }) {
		return [
			{
				label: 'Configure',
				slots: {
					prefix: icon('settings'),
				},
				onClick() {
					renderDialog(h(RoleConfigureDialog, { roleId: props.roleId }));
				},
			},
			{
				label: 'Delete',
				slots: {
					prefix: icon('trash-2'),
				},
				condition: () => selectedItems.value.size > 0,
				onClick() {
					role.bulkDelete.submit(
						{
							permissions: Array.from(selectedItems.value),
						},
						{
							onSuccess: () => {
								toast.success('Items deleted successfully');
								selectedItems.value.clear();
							},
						},
					);
				},
			},
			{
				label: 'Add',
				slots: {
					prefix: icon('plus'),
				},
				onClick() {
					confirmDialog({
						title: 'Add Permission',
						message: '',
						fields: [
							{
								label: `Select ${currentDropdownOption.value.doctype.replace(
									'Release Group',
									'Bench Group',
								)}`,
								type: 'link',
								fieldname: 'document_name',
								options: {
									doctype: currentDropdownOption.value.doctype,
									filters: {
										name: [
											'not in',
											permissions.data.map(
												(p) => p[currentDropdownOption.value.fieldname],
											) || '',
										],
										status: ['!=', 'Archived'],
									},
								},
							},
						],
						primaryAction: {
							label: 'Add',
							onClick({ values }) {
								let key = currentDropdownOption.value.fieldname;

								toast.promise(
									docInsert.submit({
										doc: {
											doctype: 'Press Role Permission',
											role: props.roleId,
											[key]: values.document_name,
										},
									}),
									{
										loading: 'Adding permission...',
										success() {
											permissions.reload();
											return 'Permission added successfully';
										},
										error: (e) => getToastErrorMessage(e),
									},
								);
							},
						},
					});
				},
			},
		].filter((action) => (action.condition ? action.condition() : true));
	},
});
</script>
