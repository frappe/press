<template>
	<div class="space-y-5">
		<div class="ml-auto mr-0 w-max space-x-2">
			<Button
				icon="refresh-cw"
				variant="subtle"
				@click="() => roles.refresh()"
			/>
			<Button icon="plus" variant="solid" />
		</div>
		<div class="grid grid-cols-3 gap-4 text-base">
			<RouterLink
				v-for="role in roles.data"
				:to="{
					name: 'SettingsPermissionRolePermissions',
					params: {
						id: role.name,
					},
				}"
			>
				<div
					class="px-4 h-36 flex flex-col justify-evenly rounded shadow cursor-pointer hover:shadow-lg transition"
				>
					<div class="font-medium">{{ role.title }}</div>
					<div class="flex flex-wrap gap-1">
						<div v-for="permission in permissions(role)">
							<Badge
								variant="subtle"
								:theme="permission.color"
								:label="permission.label"
							/>
						</div>
					</div>
					<div>
						<div class="flex items-center -space-x-2">
							<Tooltip
								v-for="user in role.users.slice(0, 3)"
								:text="user.full_name"
								:hover-delay="1"
								:placement="'top'"
							>
								<Avatar
									:shape="'circle'"
									:ref_for="true"
									:image="user.user_image"
									:label="user.full_name"
									size="lg"
									class="border border-white"
								/>
							</Tooltip>
							<div
								v-if="role.users.length > 4"
								class="flex items-center justify-center relative shrink-0 w-7 h-7 rounded-full bg-gray-300 border border-white"
							>
								<div class="text-xs">+{{ role.users.length - 3 }}</div>
							</div>
						</div>
					</div>
				</div>
			</RouterLink>
		</div>
	</div>
</template>

<script setup>
import { createListResource } from 'frappe-ui';

const roles = createListResource({
	doctype: 'Press Role',
	fields: [
		'name',
		'title',
		'admin_access',
		'allow_server_creation',
		'allow_site_creation',
		'allow_bench_creation',
		'allow_webhook_configuration',
		{ users: ['user', 'user.full_name', 'user.user_image'] },
	],
	sortBy: 'title',
	sortOrder: 'asc',
	auto: true,
});

const permissions = (role) => {
	return [
		{
			key: 'admin_access',
			label: 'Admin',
			color: 'red',
		},
		{
			key: 'allow_site_creation',
			label: 'Site',
			color: 'green',
		},
		{
			key: 'allow_bench_creation',
			label: 'Bench',
			color: 'green',
		},
		{
			key: 'allow_server_creation',
			label: 'Server',
			color: 'green',
		},
		{
			key: 'allow_webhook_configuration',
			label: 'Webhook',
			color: 'green',
		},
	].filter((permission) => role[permission.key]);
};
</script>
