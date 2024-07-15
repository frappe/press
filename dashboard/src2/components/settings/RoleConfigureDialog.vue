<template>
	<Dialog
		v-if="role"
		:options="{ title: `${role.title}`, size: 'xl' }"
		v-model="show"
	>
		<template v-slot:body-content>
			<FTabs
				class="[&>div]:pl-0"
				:tabs="[
					{
						label: 'Members',
						value: 'members'
					},
					{
						label: 'Settings',
						value: 'settings'
					}
				]"
				v-model="tabIndex"
				v-slot="{ tab }"
			>
				<div v-if="tab.value === 'members'" class="text-base">
					<div class="my-4 flex gap-2">
						<div class="flex-1">
							<Autocomplete
								:options="autoCompleteList"
								v-model="member"
								placeholder="Select a member to add"
							/>
						</div>
						<Button
							variant="solid"
							label="Add Member"
							:disabled="!member?.value"
							:loading="$resources.role.addUser?.loading"
							@click="() => addUser(member.value)"
						/>
					</div>
					<div class="rounded border-2 border-dashed p-3">
						<div class="mb-1 text-gray-600">Members</div>
						<div
							v-if="roleUsers.length === 0"
							class="p-4 text-center text-gray-500"
						>
							<span>No members added to this role.</span>
						</div>
						<div v-else class="flex flex-col divide-y">
							<div
								v-for="user in roleUsers"
								class="flex justify-between py-2.5"
							>
								<UserWithAvatarCell
									:avatarImage="user.user_image"
									:fullName="user.full_name"
									:email="user.user"
									:key="user.user"
								/>
								<Button @click="() => removeUser(user.user)">
									<template #icon>
										<i-lucide-x class="h-4 w-4 text-gray-600" />
									</template>
								</Button>
							</div>
						</div>
					</div>
				</div>
				<div v-else-if="tab.value === 'settings'" class="mt-4 text-base">
					<div class="space-y-3">
						<div class="space-y-3 rounded border p-4">
							<Switch
								v-model="allowBilling"
								label="Allow Billing Access"
								description="Grant users belonging to this role access to billing page"
							/>
							<Switch
								v-model="allowApps"
								label="Allow Apps Access"
								description="Grant users belonging to this role access to apps page"
							/>
							<Switch
								v-if="$team.doc.erpnext_partner"
								v-model="allowPartner"
								label="Allow Partner Access"
								description="Grant users belonging to this role access to partner page"
							/>
						</div>
						<div class="space-y-3 rounded border p-4">
							<Switch
								v-model="allowSiteCreation"
								label="Allow Site Creation"
								description="Newly created sites will be given access to users of this role"
							/>
							<Switch
								v-model="allowBenchCreation"
								label="Allow Bench Creation"
								description="Newly created benches will be given access to users of this role"
							/>
							<Switch
								v-model="allowServerCreation"
								label="Allow Server Creation"
								description="Newly created servers will be given access to users of this role"
							/>
						</div>
					</div>
				</div>
			</FTabs>
		</template>
	</Dialog>
</template>

<script>
import { Switch, Tabs } from 'frappe-ui';
import { toast } from 'vue-sonner';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';

export default {
	props: {
		roleId: { type: String, required: true }
	},
	components: {
		UserWithAvatarCell,
		FTabs: Tabs,
		Switch
	},
	data() {
		return {
			member: {},
			show: true,
			tabIndex: 0
		};
	},
	resources: {
		role() {
			return {
				type: 'document',
				doctype: 'Press Role',
				name: this.roleId,
				whitelistedMethods: {
					addUser: 'add_user',
					removeUser: 'remove_user',
					bulkDelete: 'delete_permissions'
				}
			};
		}
	},
	computed: {
		role() {
			return this.$resources.role.doc;
		},
		roleUsers() {
			return this.role?.users || [];
		},
		autoCompleteList() {
			const isNotGroupMember = u =>
				!this.roleUsers.map(({ user }) => user).includes(u);
			return this.$team.doc.team_members
				?.filter(({ user }) => isNotGroupMember(user))
				.map(({ user }) => ({ label: user, value: user }));
		},
		allowBilling: {
			get() {
				return !!this.role?.allow_billing;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_billing: value
					},
					{ onSuccess: this.$session.roles.reload }
				);
			}
		},
		allowApps: {
			get() {
				return !!this.role?.allow_apps;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_apps: value
					},
					{ onSuccess: this.$session.roles.reload }
				);
			}
		},
		allowPartner: {
			get() {
				return !!this.role?.allow_partner;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_partner: value
					},
					{ onSuccess: this.$session.roles.reload }
				);
			}
		},
		allowSiteCreation: {
			get() {
				return !!this.role?.allow_site_creation;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_site_creation: value
					},
					{ onSuccess: this.$session.roles.reload }
				);
			}
		},
		allowBenchCreation: {
			get() {
				return !!this.role?.allow_bench_creation;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_bench_creation: value
					},
					{ onSuccess: this.$session.roles.reload }
				);
			}
		},
		allowServerCreation: {
			get() {
				return !!this.role?.allow_server_creation;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_server_creation: value
					},
					{ onSuccess: this.$session.roles.reload }
				);
			}
		}
	},
	methods: {
		addUser(user) {
			return toast.promise(this.$resources.role.addUser.submit({ user }), {
				loading: `Adding ${user} to ${this.role.title}`,
				success: () => {
					this.member = {};
					return `${user} added to ${this.role.title}`;
				},
				error: e => (e.messages.length ? e.messages.join('\n') : e.message)
			});
		},
		removeUser(user) {
			return toast.promise(this.$resources.role.removeUser.submit({ user }), {
				loading: `Removing ${user} from ${this.role.title}`,
				success: () => `${user} removed from ${this.role.title}`,
				error: e => (e.messages.length ? e.messages.join('\n') : e.message)
			});
		}
	}
};
</script>
