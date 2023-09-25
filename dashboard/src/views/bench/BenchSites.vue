<template>
	<div class="space-y-8">
		<Table
			:columns="[
				{ label: 'Site Name', name: 'name', width: 2 },
				{ label: 'Status', name: 'status' },
				{ label: 'Region', name: 'region' },
				{ label: 'Tags', name: 'tags' },
				{ label: 'Plan', name: 'plan' },
				{ label: '', name: 'actions', width: 0.5 }
			]"
			:rows="versions"
			v-slot="{ rows, columns }"
		>
			<TableHeader v-if="rows.length !== 0" class="mb-4 hidden sm:grid" />
			<div class="flex items-center justify-center">
				<LoadingText class="mt-8" v-if="$resources.versions.loading" />
				<div v-else-if="rows.length === 0" class="mt-8">
					<div class="text-base text-gray-700">No Benches</div>
				</div>
			</div>
			<div
				v-for="(group, i) in rows"
				:key="group.name"
				class="mb-4 rounded border"
			>
				<div
					class="flex w-full items-center justify-between rounded-t bg-gray-50 px-3 py-2 text-base"
				>
					<span
						class="cursor-default font-semibold text-gray-900"
						:title="
							'Deployed on ' +
							formatDate(group.deployed_on, 'DATETIME_SHORT', true)
						"
					>
						{{ group.name }}
						<Badge :label="group.status" class="ml-2" />
					</span>
					<div class="flex items-center space-x-2">
						<Button
							variant="ghost"
							label="Show Apps"
							@click="
								selectedVersionIndex = i;
								showAppsDialog = true;
							"
						/>
						<Dropdown :options="benchDropdownItems(i)">
							<template v-slot="{ open }">
								<Button variant="ghost">
									<template #icon>
										<FeatherIcon name="more-horizontal" class="h-4 w-4" />
									</template>
								</Button>
							</template>
						</Dropdown>
					</div>
				</div>
				<div
					v-if="!group.sites?.length"
					class="flex items-center justify-center border-b py-4.5"
				>
					<div class="text-base text-gray-600">No Sites</div>
				</div>
				<TableRow
					v-for="(row, index) in group.sites"
					:key="row.name"
					:row="row"
					:class="index === 0 ? 'rounded-b' : 'rounded'"
				>
					<TableCell v-for="column in columns">
						<Badge v-if="column.name === 'status'" :label="$siteStatus(row)" />
						<div
							v-else-if="column.name === 'tags' && row.tags"
							class="hidden space-x-1 sm:flex"
						>
							<Badge
								v-for="(tag, i) in row.tags.slice(0, 1)"
								theme="blue"
								:label="tag"
							/>
							<Tooltip
								v-if="row.tags.length > 1"
								:text="row.tags.slice(1).join(', ')"
							>
								<Badge
									v-if="row.tags.length > 1"
									:label="`+${row.tags.length - 1}`"
								/>
							</Tooltip>
						</div>
						<span v-else-if="column.name === 'plan'" class="hidden sm:block">
							{{
								row.plan
									? `${$planTitle(row.plan)}${
											row.plan.price_usd > 0 ? '/mo' : ''
									  }`
									: ''
							}}
						</span>
						<div v-else-if="column.name === 'region'" class="hidden sm:block">
							<img
								v-if="row.server_region_info?.image"
								class="h-4"
								:src="row.server_region_info.image"
								:alt="`Flag of ${row.server_region_info.title}`"
								:title="row.server_region_info.title"
							/>
							<span class="text-base text-gray-700" v-else>
								{{ row.server_region_info?.title }}
							</span>
						</div>
						<div class="w-full text-right" v-else-if="column.name == 'actions'">
							<Dropdown @click.prevent :options="dropdownItems(row)">
								<template v-slot="{ open }">
									<Button
										:variant="open ? 'subtle' : 'ghost'"
										icon="more-horizontal"
									/>
								</template>
							</Dropdown>
						</div>
						<span v-else>{{ row[column.name] || '' }}</span>
					</TableCell>
				</TableRow>
			</div>
		</Table>
	</div>

	<Dialog :options="{ title: 'Apps' }" v-model="showAppsDialog">
		<template #body-content>
			<ListItem
				class="mb-3 flex items-center rounded-md border px-4 py-3 shadow ring-1 ring-gray-300"
				v-for="app in versions[selectedVersionIndex].apps"
				:key="app.app"
				:title="app.app"
				:subtitle="`${app.repository_owner}/${app.repository}:${app.branch}`"
			>
				<template #actions>
					<CommitTag
						:tag="app.tag || app.hash.substr(0, 7)"
						class="ml-2"
						:link="`${app.repository_url}/commit/${app.hash}`"
					/>
				</template>
			</ListItem>
		</template>
	</Dialog>

	<Dialog
		:options="{
			title: 'Login As Administrator',
			actions: [
				{
					label: 'Proceed',
					variant: 'solid',
					onClick: proceedWithLoginAsAdmin
				}
			]
		}"
		v-model="showReasonForAdminLoginDialog"
	>
		<template #body-content>
			<FormControl
				label="Reason for logging in as Administrator"
				type="textarea"
				v-model="reasonForAdminLogin"
				required
			/>
			<ErrorMessage class="mt-3" :message="errorMessage" />
		</template>
	</Dialog>

	<Dialog :options="{ title: 'SSH Access' }" v-model="showSSHDialog">
		<template v-slot:body-content>
			<div v-if="certificate" class="space-y-4" style="max-width: 29rem">
				<div class="space-y-2">
					<h4 class="text-base font-semibold text-gray-700">Step 1</h4>
					<div class="space-y-1">
						<p class="text-base">
							Execute the following shell command to store the SSH certificate
							locally.
						</p>
						<ClickToCopyField :textContent="certificateCommand" />
					</div>
				</div>

				<div class="space-y-2">
					<h4 class="text-base font-semibold text-gray-700">Step 2</h4>
					<div class="space-y-1">
						<p class="text-base">
							Execute the following shell command to SSH into your bench
						</p>
						<ClickToCopyField :textContent="sshCommand" />
					</div>
				</div>
			</div>
			<div v-if="!certificate">
				<p class="mb-4 text-base">
					You will need an SSH certificate to get SSH access to your bench. This
					certificate will work only with your public-private key pair and will
					be valid for 6 hours.
				</p>
				<p class="text-base">
					Please refer to the
					<a href="/docs/benches/ssh" class="underline"
						>SSH Access documentation</a
					>
					for more details.
				</p>
			</div>
		</template>
		<template #actions v-if="!certificate">
			<Button
				:loading="$resources.generateCertificate.loading"
				@click="$resources.generateCertificate.fetch()"
				variant="solid"
				class="w-full"
				>Generate SSH Certificate</Button
			>
		</template>
		<ErrorMessage
			class="mt-3"
			:message="$resources.generateCertificate.error"
		/>
	</Dialog>
	<CodeServer
		:show="showCodeServerDialog"
		@close="showCodeServerDialog = false"
		:version="versions[selectedVersionIndex]?.name"
	/>
</template>
<script>
import { loginAsAdmin } from '@/controllers/loginAsAdmin';
import Table from '@/components/Table/Table.vue';
import TableHeader from '@/components/Table/TableHeader.vue';
import TableRow from '@/components/Table/TableRow.vue';
import TableCell from '@/components/Table/TableCell.vue';
import CommitTag from '@/components/utils/CommitTag.vue';
import CodeServer from '@/views/spaces/CreateCodeServerDialog.vue';
import ClickToCopyField from '@/components/ClickToCopyField.vue';
import { notify } from '@/utils/toast';

export default {
	name: 'BenchSites',
	props: ['bench', 'benchName'],
	components: {
		Table,
		TableHeader,
		TableRow,
		TableCell,
		ClickToCopyField,
		CommitTag,
		CodeServer
	},
	data() {
		return {
			reasonForAdminLogin: '',
			errorMessage: null,
			selectedVersionIndex: 0,
			showSSHDialog: false,
			showCodeServerDialog: false,
			showAppsDialog: false,
			showReasonForAdminLoginDialog: false,
			siteForLogin: null
		};
	},
	resources: {
		versions() {
			return {
				url: 'press.api.bench.versions',
				params: {
					name: this.benchName
				},
				auto: true
			};
		},
		loginAsAdmin() {
			return loginAsAdmin('placeholderSite'); // So that RM does not yell at first load
		},
		getCertificate() {
			return {
				url: 'press.api.bench.certificate',
				params: { name: this.benchName },
				auto: true
			};
		},
		generateCertificate() {
			return {
				url: 'press.api.bench.generate_certificate',
				params: { name: this.bench?.name },
				onSuccess() {
					this.$resources.getCertificate.reload();
				}
			};
		},
		restartBench() {
			return {
				url: 'press.api.bench.restart',
				params: {
					name: this.versions[this.selectedVersionIndex]?.name
				}
			};
		},
		updateAllSites() {
			return {
				url: 'press.api.bench.update',
				params: {
					name: this.versions[this.selectedVersionIndex]?.name
				},
				onSuccess() {
					notify({
						title: 'Site update scheduled successfully',
						message: `All sites in ${
							this.versions[this.selectedVersionIndex]?.name
						} will be updated to the latest version`,
						icon: 'check',
						color: 'green'
					});
				},
				onError(e) {
					notify({
						title: 'Error',
						message: e.messages.join(', '),
						icon: 'x',
						color: 'red'
					});
				}
			};
		}
	},
	methods: {
		dropdownItems(site) {
			return [
				{
					label: 'Visit Site',
					onClick: () => {
						window.open(`https://${site.name}`, '_blank');
					}
				},
				{
					label: 'Login As Admin',
					onClick: () => {
						if (this.$account.team.name === site.team) {
							return this.$resources.loginAsAdmin.submit({
								name: site.name
							});
						}

						this.siteForLogin = site.name;
						this.showReasonForAdminLoginDialog = true;
					}
				}
			];
		},
		benchDropdownItems(i) {
			return [
				{
					label: 'View in Desk',
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/bench/${this.versions[i].name}`,
							'_blank'
						);
					},
					condition: () => this.$account.user.user_type === 'System User'
				},
				{
					label: 'SSH Access',
					onClick: () => {
						this.selectedVersionIndex = i;
						this.showSSHDialog = true;
					},
					condition: () =>
						this.versions[i].status === 'Active' &&
						this.$account.ssh_key &&
						this.versions[i].is_ssh_proxy_setup &&
						this.permissions.sshAccess
				},
				{
					label: 'View Logs',
					onClick: () => {
						this.$router.push(
							`/benches/${this.bench.name}/logs/${this.versions[i].name}/`
						);
					},
					condition: () => this.versions[i].status === 'Active'
				},
				{
					label: 'Update All Sites',
					onClick: () => {
						this.selectedVersionIndex = i;
						this.$resources.updateAllSites.submit();
					},
					condition: () =>
						this.versions[i].status === 'Active' &&
						i > 0 &&
						this.versions[i].sites.length > 0
				},
				{
					label: 'Restart Bench',
					onClick: () => {
						this.selectedVersionIndex = i;
						this.confirmRestart();
					},
					condition: () =>
						this.versions[i].status === 'Active' &&
						this.permissions.restartBench
				},
				{
					label: 'Create Code Server',
					onClick: () => {
						this.selectedVersionIndex = i;
						this.showCodeServerDialog = true;
					},
					condition: () => this.$account.team.code_servers_enabled
				}
			].filter(d => (d.condition ? d.condition() : true));
		},
		proceedWithLoginAsAdmin() {
			this.errorMessage = '';

			if (!this.reasonForAdminLogin.trim()) {
				this.errorMessage = 'Reason is required';
				return;
			}

			this.$resources.loginAsAdmin.submit({
				name: this.siteForLogin,
				reason: this.reasonForAdminLogin
			});

			this.showReasonForAdminLoginDialog = false;
		},
		confirmRestart() {
			this.$confirm({
				title: 'Restart Bench',
				message: `
					<b>bench restart</b> command will be executed on your bench. This will temporarily stop all web and backgound workers. Are you sure
					you want to run this command?
				`,
				actionLabel: 'Restart Bench',
				actionColor: 'red',
				action: closeDialog => {
					this.$resources.restartBench.submit();
					closeDialog();
				}
			});
		}
	},
	computed: {
		permissions() {
			return {
				restartBench: this.$account.hasPermission(
					this.benchName,
					'press.api.bench.restart'
				),
				sshAccess: this.$account.hasPermission(
					this.benchName,
					'press.api.bench.generate_certificate'
				)
			};
		},
		versions() {
			if (!this.$resources.versions.data) return [];

			for (let version of this.$resources.versions.data) {
				for (let site of version.sites) {
					site.route = {
						name: 'SiteOverview',
						params: {
							siteName: site.name
						}
					};
				}
			}

			return this.$resources.versions.data;
		},
		certificate() {
			return this.$resources.getCertificate.data;
		},
		sshCommand() {
			if (this.versions[this.selectedVersionIndex]) {
				return `ssh ${this.versions[this.selectedVersionIndex]?.name}@${
					this.versions[this.selectedVersionIndex]?.proxy_server
				} -p 2222`;
			}
			return null;
		},
		certificateCommand() {
			if (this.certificate) {
				return `echo '${this.certificate.ssh_certificate?.trim()}' > ~/.ssh/id_${
					this.certificate.key_type
				}-cert.pub`;
			}
			return null;
		}
	}
};
</script>
