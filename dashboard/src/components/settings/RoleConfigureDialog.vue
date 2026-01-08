<template>
	<Dialog
		v-if="role"
		:options="{ title: `${role.title}`, size: 'xl' }"
		v-model="show"
	>
		<template v-slot:body-content>
			<FTabs
				:tabs="[
					{
						label: 'Members',
						value: 'members',
					},
					{
						label: 'Settings',
						value: 'settings',
					},
				]"
				v-model="tabIndex"
			>
				<template #tab-item="{ tab }">
					<div
						class="flex cursor-pointer items-center gap-1.5 py-3 text-base text-gray-600 duration-300 ease-in-out hover:border-gray-400 hover:text-gray-900 focus:outline-none focus:transition-none [&>div]:pl-0"
					>
						<span>{{ tab.label }}</span>
					</div>
				</template>
				<template #tab-panel="{ tab }">
					<div v-if="tab.value === 'members'" class="text-base">
						<div class="my-4 flex gap-2">
							<div class="flex-1">
								<FormControl
									type="combobox"
									:options="autoCompleteList"
									:modelValue="member?.value"
									@update:modelValue="
										member = autoCompleteList.find(
											(option) => option.value === $event,
										)
									"
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
						<div class="rounded border px-3">
							<div class="mt-2 text-gray-600">Members</div>
							<div
								v-if="roleUsers.length === 0"
								class="p-6 text-center text-gray-500"
							>
								<span>No members added to this role.</span>
							</div>
							<div v-else class="flex flex-col divide-y">
								<div
									v-for="user in roleUsers"
									class="flex justify-between py-3"
								>
									<UserWithAvatarCell
										:avatarImage="user.user_image"
										:fullName="user.full_name"
										:email="user.user"
										:key="user.user"
									/>
									<Button variant="ghost" @click="() => removeUser(user.user)">
										<template #icon>
											<lucide-x class="h-4 w-4 text-gray-600" />
										</template>
									</Button>
								</div>
							</div>
						</div>
					</div>
					<div v-else-if="tab.value === 'settings'" class="mt-4 text-base">
						<div class="space-y-3">
							<div class="rounded border p-4">
								<Switch
									class="ml-2"
									v-model="adminAccess"
									label="Admin Access"
									description="Grants team owner like access to the members. Includes access to all pages and settings."
								/>
							</div>
							<div class="space-y-1 rounded border p-4">
								<h2 class="mb-2 ml-2 font-semibold">Page Access</h2>
								<Switch
									v-model="allowBilling"
									label="Allow Billing Access"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowApps"
									label="Allow Apps Access"
									:disabled="adminAccess"
								/>
								<Switch
									v-if="$team.doc.erpnext_partner"
									v-model="allowPartner"
									label="Allow Partner Access"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowSiteCreation"
									label="Allow Site Creation"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowBenchCreation"
									label="Allow Bench Group Creation"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowServerCreation"
									label="Allow Server Creation"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowWebhookConfiguration"
									label="Allow Webhook Configuration"
									:disabled="adminAccess"
								/>
							</div>
							<div v-if="allowPartner" class="space-y-1 rounded border p-4">
								<h2 class="mb-2 ml-2 font-semibold">Partner Permissions</h2>
								<Switch
									v-model="allowDashboard"
									label="Allow Dashboard Access"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowLeads"
									label="Allow Leads Access"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowCustomer"
									label="Allow Customer Access"
									:disabled="adminAccess"
								/>
								<Switch
									v-model="allowContribution"
									label="Allow Contribution Access"
									:disabled="adminAccess"
								/>
							</div>
						</div>
					</div>
				</template>
			</FTabs>
		</template>
	</Dialog>
</template>

<script>
import { Switch, Tabs } from 'frappe-ui';
import { toast } from 'vue-sonner';
import UserWithAvatarCell from '../UserWithAvatarCell.vue';
import { getToastErrorMessage } from '../../utils/toast';

export default {
	props: {
		roleId: { type: String, required: true },
	},
	components: {
		UserWithAvatarCell,
		FTabs: Tabs,
		Switch,
	},
	data() {
		return {
			member: {},
			show: true,
			tabIndex: 0,
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
					bulkDelete: 'delete_permissions',
				},
			};
		},
	},
	computed: {
		role() {
			return this.$resources.role.doc;
		},
		roleUsers() {
			return this.role?.users || [];
		},
		autoCompleteList() {
			const isNotGroupMember = (u) =>
				!this.roleUsers.map(({ user }) => user).includes(u);
			return this.$team.doc.team_members
				?.filter(({ user }) => isNotGroupMember(user))
				.map(({ user }) => ({ label: user, value: user }));
		},
		adminAccess: {
			get() {
				return !!this.role?.admin_access;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						admin_access: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowBilling: {
			get() {
				return !!this.role?.allow_billing;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_billing: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowApps: {
			get() {
				return !!this.role?.allow_apps;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_apps: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowPartner: {
			get() {
				return !!this.role?.allow_partner;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_partner: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowSiteCreation: {
			get() {
				return !!this.role?.allow_site_creation;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_site_creation: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowBenchCreation: {
			get() {
				return !!this.role?.allow_bench_creation;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_bench_creation: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowServerCreation: {
			get() {
				return !!this.role?.allow_server_creation;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_server_creation: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowWebhookConfiguration: {
			get() {
				return !!this.role?.allow_webhook_configuration;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_webhook_configuration: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowDashboard: {
			get() {
				return !!this.role?.allow_dashboard;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_dashboard: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowLeads: {
			get() {
				return !!this.role?.allow_leads;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_leads: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowCustomer: {
			get() {
				return !!this.role?.allow_customer;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_customer: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
		allowContribution: {
			get() {
				return !!this.role?.allow_contribution;
			},
			set(value) {
				this.$resources.role.setValue.submit(
					{
						allow_contribution: value,
					},
					{ onSuccess: this.$session.roles.reload },
				);
			},
		},
	},
	methods: {
		addUser(user) {
			return toast.promise(this.$resources.role.addUser.submit({ user }), {
				loading: `Adding ${user} to ${this.role.title}`,
				success: () => {
					this.member = {};
					return `${user} added to ${this.role.title}`;
				},
				error: (e) => getToastErrorMessage(e),
			});
		},
		removeUser(user) {
			return toast.promise(this.$resources.role.removeUser.submit({ user }), {
				loading: `Removing ${user} from ${this.role.title}`,
				success: () => `${user} removed from ${this.role.title}`,
				error: (e) => getToastErrorMessage(e),
			});
		},
	},
};
</script>
