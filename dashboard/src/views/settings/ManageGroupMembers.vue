<template>
	<Dialog
		:options="{ title: `Manage Members for ${group.title}` }"
		:modelValue="show"
		@after-leave="
			() => {
				$emit('close', true);
				this.memberEmail = '';
			}
		"
	>
		<template v-slot:body-content>
			<LoadingText v-if="$resources.groupUsers.loading" />
			<div v-else>
				<span
					v-if="$resources.groupUsers.data.length === 0"
					class="text-gray-500 text-center"
				>
					No members added to this group.
				</span>
				<ListItem
					v-else
					v-for="user in $resources.groupUsers.data"
					:title="user"
					:key="user"
				>
					<template #actions>
						<Button
							icon="trash"
							@click="
								() =>
									$resources.removeGroupUser.submit({
										name: group.name,
										user: user
									})
							"
						/>
					</template>
				</ListItem>
			</div>
		</template>
		<template v-slot:actions>
			<Autocomplete
				:options="autoCompleteList"
				v-model="member"
				placeholder="Select a member to add"
			/>
			<Button
				variant="solid"
				label="Add Member"
				class="mt-2 w-full"
				:loading="$resources.groupUsers.loading"
				@click="
					$resources.addGroupUser.submit({
						name: group.name,
						user: member.value
					})
				"
			/>
		</template>
	</Dialog>
</template>

<script>
export default {
	name: 'ManageGroupMembers',
	data() {
		return {
			member: {},
			autoCompleteList: []
		};
	},
	props: ['show', 'group'],
	watch: {
		group() {
			this.$resources.groupUsers.submit();
		}
	},
	resources: {
		removeGroupUser: {
			url: 'press.api.account.remove_permission_group_user',
			onSuccess() {
				this.$resources.groupUsers.fetch();
			}
		},
		addGroupUser: {
			url: 'press.api.account.add_permission_group_user',
			onSuccess() {
				this.$resources.groupUsers.fetch();
				this.member = {};
			}
		},
		groupUsers() {
			return {
				url: 'press.api.account.permission_group_users',
				params: {
					name: this.group.name
				},
				onSuccess(r) {
					this.autoCompleteList = this.$account.team_members
						.filter(user => {
							return (
								!r.includes(user.name) && user.name != this.$account.team.user
							);
						})
						.map(user => {
							return {
								label: user.name,
								value: user.name
							};
						});
				}
			};
		}
	}
};
</script>
