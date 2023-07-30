<template>
	<Card
		title="Domains"
		:subtitle="
			domains.data && domains.data.length
				? 'Domains pointing to your site'
				: 'No domains pointing to your site'
		"
	>
		<template #actions>
			<Button
				@click="showDialog = true"
				:disabled="site.status === 'Suspended'"
			>
				Add Domain
			</Button>
		</template>
		<div class="divide-y" v-if="domains.data">
			<div v-for="d in domains.data" :key="d.name">
				<div class="py-2">
					<div class="flex items-center">
						<div class="flex w-2/3 text-base font-medium">
							<a
								class="text-blue-500"
								:href="'https://' + d.domain"
								target="_blank"
								v-if="d.status === 'Active'"
							>
								{{ d.domain }}
							</a>
							<span v-else>{{ d.domain }}</span>
							<div
								class="flex"
								v-if="d.redirect_to_primary == 1 && d.status == 'Active'"
							>
								<FeatherIcon name="arrow-right" class="w-4 mx-1" />
								<a
									class="text-blue-500"
									:href="'https://' + d.domain"
									target="_blank"
									v-if="d.status === 'Active'"
								>
									{{ site.host_name }}
								</a>
							</div>
						</div>
						<div class="ml-auto flex items-center space-x-2">
							<Badge
								v-if="d.status == 'Active' && d.primary"
								:label="'Primary'"
							/>
							<Badge v-else-if="d.status != 'Active'" :label="d.status" />
							<Button
								v-if="d.status == 'Broken' && d.retry_count <= 5"
								:loading="$resources.retryAddDomain.loading"
								@click="
									$resources.retryAddDomain.submit({
										name: site.name,
										domain: d.domain
									})
								"
							>
								Retry
							</Button>
							<Button
								v-if="
									$resources.removeDomain.loading &&
									$resources.removeDomain.currentParams.domain == d.domain
								"
								:loading="true"
							>
								Removing domain
							</Button>
							<Dropdown v-else :options="actionItems(d)">
								<template v-slot="{ open }">
									<Button icon="more-horizontal" />
								</template>
							</Dropdown>
						</div>
					</div>
					<ErrorMessage
						v-if="d.status == 'Broken'"
						error="We encountered an error while adding the domain."
					/>
					<ErrorMessage :message="$resources.removeDomain.error" />
					<ErrorMessage :message="$resources.setHostName.error" />
				</div>
			</div>
		</div>
		<Dialog v-model="showDialog" :options="{ title: 'Add Domain' }">
			<template v-slot:body-content>
				<div class="space-y-4">
					<p class="text-base">
						To add a custom domain, you must already own it. If you don't have
						one, buy it and come back here.
					</p>
					<Input
						type="text"
						placeholder="www.example.com"
						v-model="newDomain"
						:readonly="dnsVerified"
					/>

					<div v-if="newDomain && !dnsVerified" class="text-base space-y-2">
						<p>Create one of the following DNS records</p>
						<p class="px-2">
							<span class="font-semibold text-gray-700">CNAME</span> record from
							<span class="font-semibold text-gray-700">{{ newDomain }}</span>
							to
							<span class="font-semibold text-gray-700">{{ site.name }}</span>
						</p>
						<p class="px-2">
							<span class="font-semibold text-gray-700">A</span> record from
							<span class="font-semibold text-gray-700">{{ newDomain }}</span>
							to
							<span class="font-semibold text-gray-700">{{ site.ip }}</span>
						</p>
					</div>
					<div v-if="dnsResult && !dnsResult.matched" class="space-y-2">
						<p class="text-base">
							Received following DNS query responses for
							<span class="font-semibold text-gray-700">{{ newDomain }}</span
							>.
						</p>
						<div
							v-if="newDomain && dnsResult.CNAME && !dnsResult.CNAME.matched"
							class="space-y-2"
						>
							<p class="text-base">
								<span class="font-semibold text-gray-700">CNAME</span>
							</p>
							<div
								class="flex flex-row items-center justify-between rounded-lg border-2 p-2"
							>
								<p
									class="select-all overflow-hidden font-mono text-sm text-gray-800"
								>
									{{ dnsResult.CNAME.answer }}
								</p>
							</div>
						</div>
						<div
							v-if="newDomain && dnsResult.A && !dnsResult.A.matched"
							class="space-y-2"
						>
							<p class="text-base">
								<span class="font-semibold text-gray-700">A</span>
							</p>
							<div
								class="flex flex-row items-center justify-between rounded-lg border-2 p-2"
							>
								<p
									class="select-all overflow-hidden font-mono text-sm text-gray-800"
								>
									{{ dnsResult.A.answer }}
								</p>
							</div>
						</div>
					</div>
					<p class="flex text-base" v-if="dnsVerified === false">
						<FeatherIcon
							name="x"
							class="mr-2 h-5 w-5 rounded-full bg-red-100 p-1 text-red-500"
						/>
						DNS Verification Failed
					</p>
					<p class="flex text-base" v-if="dnsVerified === true">
						<FeatherIcon
							name="check"
							class="mr-2 h-5 w-5 rounded-full bg-green-100 p-1 text-green-500"
						/>
						DNS records successfully verified. Click on Add Domain.
					</p>
					<ErrorMessage :message="$resources.checkDNS.error" />
					<ErrorMessage :message="$resources.addDomain.error" />
					<ErrorMessage :message="$resources.retryAddDomain.error" />
				</div>
			</template>

			<template v-slot:actions>
				<Button @click="cancelAddDomainDialog()"> Cancel </Button>
				<Button
					v-if="!dnsVerified"
					class="ml-3"
					appearance="primary"
					:loading="$resources.checkDNS.loading"
					@click="
						$resources.checkDNS.submit({
							name: site.name,
							domain: newDomain
						})
					"
				>
					Verify DNS
				</Button>
				<Button
					v-if="dnsVerified"
					class="ml-3"
					appearance="primary"
					:loading="$resources.addDomain.loading"
					@click="
						$resources.addDomain.submit({
							name: site.name,
							domain: newDomain
						})
					"
				>
					Add Domain
				</Button>
			</template>
		</Dialog>
	</Card>
</template>

<script>
export default {
	name: 'SiteOverviewDomains',
	props: ['site'],
	data() {
		return {
			showDialog: false,
			newDomain: null
		};
	},
	resources: {
		domains() {
			return {
				method: 'press.api.site.domains',
				params: { name: this.site?.name },
				auto: true
			};
		},
		checkDNS: {
			method: 'press.api.site.check_dns',
			validate() {
				if (!this.newDomain) return 'Domain cannot be empty';
			}
		},
		addDomain: {
			method: 'press.api.site.add_domain',
			onSuccess() {
				this.$resources.checkDNS.reset();
				this.$resources.domains.reload();
				this.showDialog = false;
			}
		},
		removeDomain: {
			method: 'press.api.site.remove_domain',
			onSuccess() {
				this.$resources.domains.reload();
			}
		},
		retryAddDomain: {
			method: 'press.api.site.retry_add_domain',
			onSuccess() {
				this.$resources.domains.fetch();
			}
		},
		setHostName: {
			method: 'press.api.site.set_host_name',
			onSuccess() {
				this.$resources.domains.reload();
			}
		},
		setupRedirect: {
			method: 'press.api.site.set_redirect',
			onSuccess() {
				this.$resources.domains.reload();
			}
		},
		removeRedirect: {
			method: 'press.api.site.unset_redirect',
			onSuccess() {
				this.$resources.domains.reload();
			}
		}
	},
	computed: {
		domains() {
			return this.$resources.domains;
		},
		dnsVerified() {
			return this.dnsResult?.matched;
		},
		dnsResult() {
			return this.$resources.checkDNS.data;
		},
		primaryDomain() {
			return this.$resources.domains.data.filter(d => d.primary)[0].domain;
		}
	},
	watch: {
		newDomain() {
			this.$resources.checkDNS.reset();
		}
	},
	methods: {
		actionItems(domain) {
			return [
				{
					label: 'Remove',
					onClick: () => this.confirmRemoveDomain(domain.domain)
				},
				{
					label: 'Set Primary',
					condition: () => domain.status == 'Active' && !domain.primary,
					onClick: () => this.confirmSetPrimary(domain.domain)
				},
				{
					label: 'Redirect to Primary',
					condition: () =>
						domain.status == 'Active' &&
						!domain.primary &&
						!domain.redirect_to_primary,
					onClick: () => this.confirmSetupRedirect(domain.domain)
				},
				{
					label: 'Remove Redirect',
					condition: () =>
						domain.status == 'Active' &&
						!domain.primary &&
						domain.redirect_to_primary,
					onClick: () => this.confirmRemoveRedirect(domain.domain)
				}
			].filter(d => (d.condition ? d.condition() : true));
		},
		confirmRemoveDomain(domain) {
			this.$confirm({
				title: 'Remove Domain',
				message: `Are you sure you want to remove the domain <b>${domain}</b>?`,
				actionLabel: 'Remove',
				actionType: 'danger',
				action: closeDialog => {
					closeDialog();
					this.$resources.removeDomain.submit({
						name: this.site.name,
						domain: domain
					});
				}
			});
		},
		confirmSetPrimary(domain) {
			let workingRedirects = false;
			this.$resources.domains.data.forEach(d => {
				if (d.redirect_to_primary) {
					workingRedirects = true;
				}
			});

			if (workingRedirects) {
				this.$notify({
					title: 'Please Remove all Active Redirects',
					color: 'red',
					icon: 'x'
				});
			} else {
				this.$confirm({
					title: 'Set as Primary Domain',
					message: `Setting as primary will make <b>${domain}</b> the primary URL for your site. Do you want to continue?`,
					actionLabel: 'Set Primary',
					actionType: 'primary',
					action: closeDialog => {
						closeDialog();
						this.$resources.setHostName.submit({
							name: this.site.name,
							domain: domain
						});
					}
				});
			}
		},
		confirmSetupRedirect(domain) {
			this.$confirm({
				title: 'Redirect to Primary Domain',
				message: `Redirect to Primary will redirect <b>${domain}</b> to <b>${this.primaryDomain}</b>. Do you want to continue?`,
				actionLabel: 'Redirect to Primary',
				actionType: 'primary',
				action: closeDialog => {
					closeDialog();
					this.$resources.setupRedirect.submit({
						name: this.site.name,
						domain: domain
					});
				}
			});
		},
		confirmRemoveRedirect(domain) {
			this.$confirm({
				title: 'Remove Redirect',
				message: `Remove Redirect will remove previously set up redirect from <b>${domain}</b> to <b>${this.primaryDomain}</b>. Do you want to continue?`,
				actionLabel: 'Remove Redirect',
				actionType: 'primary',
				action: closeDialog => {
					closeDialog();
					this.$resources.removeRedirect.submit({
						name: this.site.name,
						domain: domain
					});
				}
			});
		},
		cancelAddDomainDialog() {
			this.showDialog = false;
			this.newDomain = null;
			this.$resources.checkDNS.reset();
		}
	}
};
</script>
