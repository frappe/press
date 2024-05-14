<template>
	<div class="mb-5 flex items-center gap-2">
		<Tooltip text="All Roles">
			<Button :route="{ name: 'SettingsPermissionRoles' }" class="">
				<template #icon>
					<i-lucide-arrow-left class="h-4 w-4 text-gray-700" />
				</template>
			</Button>
		</Tooltip>
		<h3 class="text-lg font-medium text-gray-900">
			{{ role.doc?.title }}
		</h3>
	</div>
	<ObjectList :options="rolePermissions">
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

		<!-- <template #header-right="{ listResource }">
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
		</template> -->
	</ObjectList>
</template>

<script setup>
import {
	Button,
	Dropdown,
	createDocumentResource,
	createResource
} from 'frappe-ui';
import { computed, h, ref } from 'vue';
import LucideAppWindow from '~icons/lucide/app-window';
import ObjectList from '../ObjectList.vue';
import PermissionGroupPermissionCell from './PermissionGroupPermissionCell.vue';
import { toast } from 'vue-sonner';
import { confirmDialog, icon } from '../../utils/components';

const props = defineProps({
	roleId: { type: String, required: true }
});

const role = createDocumentResource({
	doctype: 'Press Role',
	name: props.roleId,
	auto: true,
	whitelistedMethods: {
		getUsers: 'get_users',
		updatePermissions: 'update_permissions'
	}
});

const docInsert = createResource({
	url: 'press.api.client.insert'
});

const dropdownOptions = [
	{ label: 'Allowed Sites', doctype: 'Site', dt: 'site' },
	{ label: 'Allowed Benches', doctype: 'Release Group', dt: 'release_group' },
	{ label: 'Allowed Servers', doctype: 'Server', dt: 'server' }
];
const currentDropdownOption = ref(dropdownOptions[0]);
function getDropdownOptions(listResource) {
	return dropdownOptions.map(option => {
		return {
			...option,
			onClick: () => {
				currentDropdownOption.value = option;
				let filters = {
					role: props.roleId
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
			}
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
		'server.title as server_title'
	],
	filters: {
		role: props.roleId,
		site: ['is', 'set']
	},
	selectable: true,
	columns: [
		{
			label: computed(() =>
				currentDropdownOption.value.doctype.replace('Release Group', 'Bench')
			),
			format(_value, row) {
				return (
					row.site_host_name || row.release_group_title || row.server_title
				);
			}
		}
	],
	selectBannerOptions(d) {
		return h('div', { class: 'flex gap-2' }, [
			h(Button, {
				variant: 'ghost',
				label: 'Delete',
				slots: {
					prefix: icon('trash')
				}
			})
		]);
	},
	actions({ listResource: permissions }) {
		return [
			{
				label: 'Add',
				slots: {
					prefix: icon('plus')
				},
				onClick() {
					confirmDialog({
						title: 'Add Permission',
						message: '',
						fields: [
							{
								label: `Select ${currentDropdownOption.value.doctype.replace(
									'Release Group',
									'Bench'
								)}`,
								type: 'link',
								fieldname: 'document_name',
								options: {
									doctype: currentDropdownOption.value.doctype,
									filters: {
										name: [
											'not in',
											permissions.data.map(
												p => p[currentDropdownOption.value.dt]
											) || ''
										],
										status: ['!=', 'Archived']
									}
								}
							}
						],
						primaryAction: {
							label: 'Add',
							onClick({ values }) {
								let key = currentDropdownOption.value.dt;

								toast.promise(
									docInsert.submit({
										doc: {
											doctype: 'Press Role Permission',
											role: props.roleId,
											[key]: values.document_name
										}
									}),
									{
										loading: 'Adding permission...',
										success() {
											permissions.reload();
											return 'Permission added successfully';
										},
										error: e =>
											e.messages.length
												? e.messages.join('\n')
												: 'An error occurred'
									}
								);
							}
						}
					});
				}
			}
		];
	}
});
</script>
