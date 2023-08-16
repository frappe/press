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
			<TableHeader />
			<div class="flex items-center justify-center">
				<LoadingText class="mt-8" v-if="$resources.versions.loading" />
				<div v-else-if="rows.length === 0" class="mt-8">
					<div class="text-base text-gray-700">No Items</div>
				</div>
			</div>
			<div v-for="(group, i) in rows" :key="group.name">
				<div
					v-if="group.sites?.length"
					class="flex w-full items-center justify-between border-b bg-gray-50 px-3 py-2 text-base"
				>
					<span
						class="cursor-default font-semibold text-gray-900"
						:title="
							'Deployed on ' +
							formatDate(group.deployed_on, 'DATETIME_SHORT', true)
						"
					>
						{{ group.name }}
					</span>
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

				<TableRow v-for="row in group.sites" :key="row.name" :row="row">
					<TableCell v-for="column in columns">
						<Badge
							class="ring-1 ring-white"
							v-if="column.name === 'status'"
							:label="$siteStatus(row)"
						/>
						<div
							v-else-if="column.name === 'tags' && row.tags"
							class="-space-x-5"
						>
							<Badge
								class="ring-1 ring-white"
								v-for="(tag, i) in row.tags.slice(0, 2)"
								:theme="$getColorBasedOnString(i)"
								:label="tag"
							/>
							<Badge
								class="ring-1 ring-white"
								v-if="row.tags.length > 2"
								:label="`+${row.tags.length - 2}`"
							/>
						</div>
						<span v-else-if="column.name === 'plan'">
							{{ row.plan ? `${$planTitle(row.plan)}/mo` : '' }}
						</span>
						<div v-else-if="column.name === 'region'">
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
				method: 'press.api.bench.versions',
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
				method: 'press.api.bench.certificate',
				params: { name: this.bench?.name },
				auto: true
			};
		},
		generateCertificate() {
			return {
				method: 'press.api.bench.generate_certificate',
				params: { name: this.bench?.name },
				onSuccess() {
					this.$resources.getCertificate.reload();
				}
			};
		},
		restartBench() {
			return {
				method: 'press.api.bench.restart',
				params: {
					bench: this.versions[this.selectedVersionIndex]?.name
				}
			};
		},
		updateAllSites() {
			return {
				method: 'press.api.bench.update',
				params: {
					bench: this.versions[this.selectedVersionIndex]?.name
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
					label: 'Show App Versions',
					onClick: () => {
						this.selectedVersionIndex = i;
						this.showAppsDialog = true;
					}
				},
				this.$account.user.user_type === 'System User' && {
					label: 'View in Desk',
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/bench/${this.versions[i].name}`,
							'_blank'
						);
					}
				},
				this.versions[i].status === 'Active' &&
					this.$account.ssh_key &&
					this.versions[i].is_ssh_proxy_setup && {
						label: 'SSH Access',
						onClick: () => {
							this.selectedVersionIndex = i;
							this.showSSHDialog = true;
						}
					},
				this.versions[i].status === 'Active' && {
					label: 'View Logs',
					onClick: () => {
						this.$router.push(
							`/benches/${this.bench.name}/logs/${this.versions[i].name}/`
						);
					}
				},
				this.versions[i].status === 'Active' &&
					i > 0 &&
					this.versions[i].sites.length > 0 && {
						label: 'Update All Sites',
						onClick: () => {
							this.selectedVersionIndex = i;
							this.$resources.updateAllSites.submit();
							this.$notify({
								title: 'Site update scheduled successfully',
								message: `All sites in ${this.versions[i]?.name} will be updated to the latest version`,
								icon: 'check',
								color: 'green'
							});
						}
					},
				this.versions[i].status === 'Active' && {
					label: 'Restart Bench',
					onClick: () => {
						this.selectedVersionIndex = i;
						this.confirmRestart();
					}
				},
				this.$account.team.code_servers_enabled && {
					label: 'Create Code Server',
					onClick: () => {
						this.selectedVersionIndex = i;
						this.showCodeServerDialog = true;
					}
				}
			];
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
