<template>
	<Dialog
		:options="{
			title: 'Add New Member',
			actions: [
				{
					label: 'Invite Member',
					variant: 'solid',
					onClick: inviteMember,
				},
			],
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl label="Email" v-model="email" />
				<div
					v-if="$resources.roles.data?.length > 0"
					class="flex items-center space-x-2"
				>
					<FormControl
						class="w-full"
						type="combobox"
						label="Select Roles"
						:options="roleOptions"
						:modelValue="selectedRole?.value"
						@update:modelValue="
							selectedRole = roleOptions.find(
								(option) => option.value === $event,
							)
						"
					/>
					<Button
						label="Add"
						icon-left="plus"
						:disabled="!selectedRole"
						@click="addRole"
						class="mt-5"
					/>
				</div>
				<div
					v-if="selectedRoles.length > 0"
					class="divide-y rounded border border-gray-300 px-1.5"
				>
					<div
						class="flex w-full items-center space-x-2 py-1.5"
						v-for="role in selectedRoles"
					>
						<div class="flex w-full items-center justify-between px-3 py-2">
							<div class="text-base text-gray-800">{{ role.label }}</div>
						</div>
						<Button
							class="ml-auto"
							variant="ghost"
							icon="x"
							@click="removeRole(role.value)"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../../utils/error';
import { getToastErrorMessage } from '../../utils/toast';

export default {
	data() {
		return {
			email: '',
			show: true,
			selectedRoles: [],
			selectedRole: null,
		};
	},
	resources: {
		roles() {
			return {
				type: 'list',
				doctype: 'Press Role',
				fields: ['name', 'title'],
				initialData: [],
				auto: true,
			};
		},
	},
	computed: {
		roleOptions() {
			return this.$resources.roles.data
				.filter((role) => {
					return !this.selectedRoles.some(
						(selectedRole) => selectedRole.value === role.name,
					);
				})
				.map((role) => ({
					label: role.title,
					value: role.name,
				}));
		},
	},
	methods: {
		addRole() {
			if (this.selectedRole) {
				this.selectedRoles.push(this.selectedRole);
				this.selectedRole = null;
			}
		},
		removeRole(roleToRemove) {
			this.selectedRoles = this.selectedRoles.filter(
				(role) => role.value !== roleToRemove,
			);
		},
		inviteMember() {
			toast.promise(
				this.$team.inviteTeamMember.submit(
					{
						email: this.email,
						roles: this.selectedRoles.map((role) => role.value),
					},
					{
						validate: () => {
							if (!this.email) {
								throw new DashboardError('Email is required');
							}
						},
					},
				),
				{
					loading: 'Sending Invite...',
					success: () => {
						this.show = false;
						return 'Invite Sent!';
					},
					error: (e) => getToastErrorMessage(e),
				},
			);
		},
	},
};
</script>
