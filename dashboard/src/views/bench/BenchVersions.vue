<template>
	<CardWithDetails
		v-if="bench"
		title="Versions"
		subtitle="Deployed versions of your bench"
		:showDetails="selectedVersion"
	>
		<div class="h-full">
			<router-link
				v-for="v in $resources.versions.data"
				class="block cursor-pointer rounded-md px-2.5"
				:class="
					selectedVersion && v.name === selectedVersion.name
						? 'bg-gray-100'
						: 'hover:bg-gray-50'
				"
				:key="v.name"
				:to="getRoute(v)"
			>
				<ListItem
					:title="v.name"
					:subtitle="
						v.deployed_on
							? `Deployed on ${formatDate(
									v.deployed_on,
									'DATETIME_SHORT',
									true
							  )}`
							: ''
					"
				>
					<template #actions>
						<Badge v-if="v.status != 'Active'" :label="v.status" />
						<Badge
							v-else
							theme="green"
							:label="`${v.sites.length} ${$plural(
								v.sites.length,
								'site',
								'sites'
							)}`"
						/>
					</template>
				</ListItem>
				<div class="border-b"></div>
			</router-link>
			<Button
				:loading="true"
				loadingText="Loading..."
				v-if="$resources.versions.loading"
			/>
		</div>
		<template #details>
			<div
				class="w-full space-y-4 border-l px-6 py-5 md:w-2/3"
				v-if="selectedVersion"
			>
				<section>
					<div class="flex items-center justify-between">
						<Button
							class="mr-3 md:hidden"
							@click="$router.back()"
							icon="chevron-left"
						/>
						<div>
							<h4 class="text-lg font-medium">{{ selectedVersion.name }}</h4>
							<p class="mt-1 text-sm text-gray-600">
								{{
									selectedVersion.deployed_on
										? `Deployed on ${formatDate(
												selectedVersion.deployed_on,
												'DATETIME_SHORT',
												true
										  )}`
										: ''
								}}
							</p>
						</div>
						<div class="hidden flex-row space-x-3 md:flex">
							<Button
								v-for="action in siteActions"
								:key="action.label"
								@click="action.action"
							>
								{{ action.label }}
							</Button>
							<Dropdown :options="versionActions">
								<template v-slot="{ open }">
									<Button icon-right="chevron-down">Actions</Button>
								</template>
							</Dropdown>
						</div>
					</div>
					<h5 class="mt-4 text-lg font-semibold">Sites</h5>
					<div class="mt-2">
						<SiteList
							class="sm:border-gray-200 sm:shadow-none"
							:sites="selectedVersion.sites || []"
							:showBenchInfo="false"
						/>
					</div>
				</section>
				<section>
					<h5 class="text-lg font-semibold">Apps</h5>
					<div class="mt-2 divide-y rounded-lg py-2 sm:border sm:px-4">
						<ListItem
							v-for="app in selectedVersion.apps"
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
					</div>
				</section>
			</div>
		</template>
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
						You will need an SSH certificate to get SSH access to your bench.
						This certificate will work only with your public-private key pair
						and will be valid for 6 hours.
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
	</CardWithDetails>
</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
import CardWithDetails from '@/components/CardWithDetails.vue';
import SiteList from '@/views/site/SiteList.vue';
import CommitTag from '@/components/utils/CommitTag.vue';
export default {
	name: 'BenchApps',
	props: ['bench', 'version'],
	components: {
		SiteList,
		CardWithDetails,
		ClickToCopyField,
		CommitTag
	},
	inject: ['viewportWidth'],
	data() {
		return { showSSHDialog: false };
	},
	resources: {
		versions() {
			return {
				method: 'press.api.bench.versions',
				params: { name: this.bench?.name },
				auto: true,
				onSuccess() {
					if (
						!this.version &&
						this.versions.data.length > 0 &&
						this.viewportWidth > 768
					) {
						this.$router.replace(this.getRoute(this.versions.data[0]));
					}
				}
			};
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
				params: { name: this.bench?.name, bench: this.selectedVersion?.name }
			};
		},
		updateAllSites() {
			return {
				method: 'press.api.bench.update',
				params: { name: this.bench?.name, bench: this.selectedVersion?.name }
			};
		}
	},
	methods: {
		getRoute(version) {
			return `/benches/${this.bench.name}/versions/${version.name}`;
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
			return this.$resources.versions;
		},
		selectedVersion() {
			if (this.version && this.versions.data) {
				return this.versions.data.find(v => v.name === this.version);
			}
			return null;
		},
		certificate() {
			return this.$resources.getCertificate.data;
		},
		sshCommand() {
			if (this.selectedVersion) {
				return `ssh ${this.selectedVersion?.name}@${this.selectedVersion?.proxy_server} -p 2222`;
			}
			return null;
		},
		certificateCommand() {
			let certificate = this.certificate;
			if (certificate) {
				return `echo '${certificate.ssh_certificate?.trim()}' > ~/.ssh/id_${
					certificate.key_type
				}-cert.pub`;
			}
			return null;
		},
		versionActions() {
			return [
				this.$account.user.user_type == 'System User' && {
					label: 'View in Desk',
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/bench/${this.selectedVersion.name}`,
							'_blank'
						);
					}
				},
				this.selectedVersion.status == 'Active' &&
					this.$account.ssh_key &&
					this.selectedVersion.is_ssh_proxy_setup && {
						label: 'SSH Access',
						onClick: () => {
							this.showSSHDialog = true;
						}
					},
				this.selectedVersion.status == 'Active' && {
					label: 'View Logs',
					onClick: () => {
						this.$router.push(
							`/benches/${this.bench.name}/logs/${this.selectedVersion.name}/`
						);
					}
				},
				this.selectedVersion.status == 'Active' &&
					this.selectedVersion.sites.length > 0 && {
						label: 'Update All Sites',
						onClick: () => {
							this.$resources.updateAllSites.submit();
							this.$notify({
								title: 'Site update scheduled successfully',
								message: `All sites in ${this.selectedVersion?.name} will be updated to the latest version`,
								icon: 'check',
								color: 'green'
							});
						}
					},
				this.selectedVersion.status == 'Active' && {
					label: 'Restart Bench',
					onClick: () => {
						this.confirmRestart();
					}
				}
			].filter(Boolean);
		}
	}
};
</script>
