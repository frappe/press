<template>
	<Button :route="{ name: 'SettingsPermissionRoles' }" class="mb-4">
		<template #prefix>
			<i-lucide-arrow-left class="h-4 w-4 text-gray-600" />
		</template>
		All roles
	</Button>
	<ObjectList :options="listOptions">
		<template #header-left="{ listResource }">
			<div class="flex items-center space-x-4">
				<h3 class="text-lg font-medium text-gray-900">
					{{ permissionGroup.doc?.title }}
				</h3>
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
			</div>
		</template>

		<template #header-right="{ listResource }">
			<Dropdown
				:options="[
					{ label: 'Allow All', onClick: () => toggleAll(listResource, true) },
					{
						label: 'Restrict All',
						onClick: () => toggleAll(listResource, false)
					},
					{ label: 'Reset All', onClick: () => resetAll(listResource) }
				]"
			>
				<Button>
					Bulk Apply
					<template #suffix>
						<FeatherIcon name="chevron-down" class="h-4 w-4 text-gray-500" />
					</template>
				</Button>
			</Dropdown>
		</template>
	</ObjectList>
</template>

<script setup>
import { Dropdown, createDocumentResource } from 'frappe-ui';
import { computed, h, inject, ref } from 'vue';
import LucideAppWindow from '~icons/lucide/app-window';
import ObjectList from '../ObjectList.vue';
import PermissionGroupPermissionCell from './PermissionGroupPermissionCell.vue';
import { toast } from 'vue-sonner';

const props = defineProps({
	groupId: { type: String, required: true }
});

const permissionGroup = createDocumentResource({
	doctype: 'Press Permission Group',
	name: props.groupId,
	auto: true,
	whitelistedMethods: {
		getUsers: 'get_users',
		updatePermissions: 'update_permissions'
	}
});

const dropdownOptions = [
	{ label: 'Site Permissions', doctype: 'Site' },
	{ label: 'Bench Permissions', doctype: 'Release Group' }
];
const currentDropdownOption = ref(dropdownOptions[0]);
function getDropdownOptions(listResource) {
	return dropdownOptions.map(option => {
		return {
			...option,
			onClick: () => {
				currentDropdownOption.value = option;
				listResource.reload();
			}
		};
	});
}

const listOptions = ref({
	onRowClick: () => {},
	rowHeight: 'unset',
	resource() {
		return {
			auto: true,
			url: 'press.api.client.run_doc_method',
			makeParams() {
				return {
					dt: 'Press Permission Group',
					dn: props.groupId,
					method: 'get_all_document_permissions',
					args: {
						doctype: currentDropdownOption.value.doctype
					}
				};
			},
			transform: data => data.message
		};
	},
	columns: [
		{
			label: computed(() => currentDropdownOption.value.label.split(' ')[0]),
			fieldname: 'document_name',
			width: 1
		},
		{
			label: 'Permissions',
			fieldname: 'permissions',
			type: 'Component',
			width: 3,
			component: ({ row }) => {
				return h(PermissionGroupPermissionCell, {
					permissions: row.permissions,
					onPermissionChange({ method, permitted }) {
						row.permissions.some(perm => {
							if (method === '*') {
								perm.permitted = permitted;
								return false; // to continue looping until all methods selected
							}
							if (perm.method === method) {
								perm.permitted = permitted;
								return true;
							}
						});
						handlePermissionChange(
							row.document_type,
							row.document_name,
							method,
							permitted
						);
					}
				});
			}
		}
	],
	primaryAction({ listResource }) {
		return {
			label: 'Update Permissions',
			variant: 'solid',
			disabled: Object.keys(updatedPermissions.value).length === 0,
			onClick() {
				updatePermissions().then(listResource.reload);
			}
		};
	}
});

const updatedPermissions = ref({});
function updatePermissions() {
	return permissionGroup.updatePermissions
		.submit({
			updated_permissions: updatedPermissions.value
		})
		.then(() => {
			toast.success('Permissions Updated');
			updatedPermissions.value = {};
		});
}

const allDocAllMethodAllowedPerm = { '*': { '*': true } };
const allDocAllMethodRestrictedPerm = { '*': { '*': false } };
const allMethodAllowedPerm = { '*': true };
const allMethodRestrictedPerm = { '*': false };

function handlePermissionChange(doctype, doc_name, method, permitted) {
	const updated = updatedPermissions.value;
	if (method === '*') {
		// allow all the methods for this document
		updated[doctype] = updated[doctype] || {};
		updated[doctype][doc_name] = permitted
			? allMethodAllowedPerm
			: allMethodRestrictedPerm;
		return;
	}
	// allow only this method for this document
	updated[doctype] = updated[doctype] || {};
	updated[doctype][doc_name] = updated[doctype][doc_name] || {};
	updated[doctype][doc_name][method] = permitted;

	updatedPermissions.value = updated;
}

function toggleAll(listResource, value) {
	if (!listResource.data?.length) return;
	listResource.data.forEach(row => {
		row.permissions.forEach(perm => {
			perm.permitted = value;
		});
	});
	const updated = updatedPermissions.value;
	const doctype = currentDropdownOption.value.doctype;
	updated[doctype] = value
		? allDocAllMethodAllowedPerm
		: allDocAllMethodRestrictedPerm;
	updatedPermissions.value = updated;
}

function resetAll(listResource) {
	updatePermissions.value = {};
	listResource.reload();
}
</script>
