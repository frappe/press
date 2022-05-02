<template>
	<CardWithDetails
		v-if="bench"
		title="Versions"
		subtitle="Deployed versions of your bench"
		:showDetails="selectedVersion"
	>
		<div>
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
							? `Deployed on ${formatDate(v.deployed_on, 'DATETIME_SHORT')}`
							: ''
					"
				>
					<template #actions>
						<Badge v-if="v.status != 'Active'" :status="v.status" />
						<Badge v-else color="green">
							{{ v.sites.length }}
							{{ $plural(v.sites.length, 'site', 'sites') }}
						</Badge>
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
												'DATETIME_SHORT'
										  )}`
										: ''
								}}
							</p>
						</div>
						<div class="flex flex-row items-center">
							<Button
								icon-left="hard-drive"
								v-if="$account.ssh_key && selectedVersion.is_ssh_proxy_setup"
								@click="showSSHDialog = true"
								class="mx-3"
							>
								SSH Access
							</Button>
							<router-link
								class="text-base text-blue-500 hover:text-blue-600"
								:to="`/benches/${bench.name}/logs/${selectedVersion.name}/`"
							>
								View Logs →
							</router-link>
						</div>
					</div>
					<h5 class="mt-4 text-lg font-semibold">Sites</h5>
					<div class="mt-2">
						<SiteList
							class="sm:border-gray-200 sm:shadow-none"
							:sites="selectedVersion.sites || []"
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
								<a
									class="ml-2 block cursor-pointer"
									:href="`${app.repository_url}/commit/${app.hash}`"
									target="_blank"
								>
									<Badge
										class="cursor-pointer hover:text-blue-500"
										color="blue"
									>
										{{ app.tag || app.hash.substr(0, 7) }}
									</Badge>
								</a>
							</template>
						</ListItem>
					</div>
				</section>
				<section>
					<h5 class="mt-4 text-lg font-semibold">Actions</h5>
					<div class="mt-2 divide-y rounded-lg py-2 sm:border sm:px-4">
						<div>
							<div class="flex items-center justify-between py-3">
								<div>
									<h3 class="text-lg">Restart</h3>
									<p class="mt-1 text-base text-gray-600">
										Restart all services on your bench
									</p>
								</div>
								<Button
									icon-left="refresh-cw"
									@click="confirmRestart()"
									class="mx-3 text-red-600"
								>
									<span class="text-red-600">Restart Bench</span>
								</Button>
							</div>
						</div>
					</div>
				</section>
			</div>
		</template>
		<Dialog title="SSH Access" v-model="showSSHDialog">
			<div v-if="certificate" class="space-y-4">
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
			<template #actions v-if="!certificate">
				<Button
					:loading="$resources.generateCertificate.loading"
					@click="$resources.generateCertificate.fetch()"
					type="primary"
					>Generate SSH Certificate</Button
				>
			</template>
			<ErrorMessage
				class="mt-3"
				:error="$resources.generateCertificate.error"
			/>
		</Dialog>
	</CardWithDetails>
</template>
<script>
import ClickToCopyField from '@/components/ClickToCopyField.vue';
import { setTransitionHooks } from 'vue';
import CardWithDetails from '../components/CardWithDetails.vue';
import SiteList from './SiteList.vue';
export default {
	name: 'BenchApps',
	props: ['bench', 'version'],
	components: {
		SiteList,
		CardWithDetails,
		ClickToCopyField
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
				actionType: 'danger',
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
		}
	}
};
</script>
