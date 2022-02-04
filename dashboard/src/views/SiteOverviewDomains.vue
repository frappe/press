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
						<div class="w-1/2 text-base font-medium">
							<a
								class="text-blue-500"
								:href="'https://' + d.domain"
								target="_blank"
								v-if="d.status === 'Active'"
							>
								{{ d.domain }}
							</a>
							<span v-else>{{ d.domain }}</span>
						</div>
						<div class="ml-auto flex items-center space-x-2">
							<Badge
								v-if="d.status != 'Active' || d.primary"
								:status="d.status"
							>
								{{ d.primary ? 'Primary' : d.status }}
							</Badge>
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
							<Dropdown v-else :items="actionItems(d)" right>
								<template v-slot="{ toggleDropdown }">
									<Button icon="more-horizontal" @click="toggleDropdown()" />
								</template>
							</Dropdown>
						</div>
					</div>
					<ErrorMessage
						v-if="d.status == 'Broken'"
						error="We encountered an error while adding the domain."
					/>
					<ErrorMessage :error="$resources.removeDomain.error" />
					<ErrorMessage :error="$resources.setHostName.error" />
				</div>
			</div>
		</div>
		<Dialog v-model="showDialog" title="Add Domain">
			<div class="space-y-4">
				<p class="text-base">
					To add a custom domain, you must already own it. If you don't have
					one, buy it and come back here.
				</p>
				<Input type="text" placeholder="www.example.com" v-model="newDomain" />

				<p class="text-base" v-if="newDomain && !dnsVerified">
					Make a <span class="font-semibold">CNAME</span> record from
					<span class="font-semibold">{{ newDomain }}</span> to
					<span class="font-semibold">{{ site.name }}</span>
				</p>
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
				<ErrorMessage :error="$resources.checkDNS.error" />
				<ErrorMessage :error="$resources.addDomain.error" />
				<ErrorMessage :error="$resources.retryAddDomain.error" />
			</div>

			<div slot="actions">
				<Button @click="showDialog = false"> Cancel </Button>
				<Button
					v-if="!dnsVerified"
					class="ml-3"
					type="primary"
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
					type="primary"
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
			</div>
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
				params: { name: this.site.name },
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
		}
	},
	computed: {
		dnsVerified() {
			return this.$resources.checkDNS.data;
		}
	},
	methods: {
		actionItems(domain) {
			return [
				{
					label: 'Remove',
					action: () => this.confirmRemoveDomain(domain.domain)
				},
				{
					label: 'Set Primary',
					condition: () => domain.status == 'Active' && !domain.primary,
					action: () => this.confirmSetPrimary(domain.domain)
				}
			].filter((d) => (d.condition ? d.condition() : true));
		},
		confirmRemoveDomain(domain) {
			this.$confirm({
				title: 'Remove Domain',
				message: `Are you sure you want to remove the domain <b>${domain}</b>?`,
				actionLabel: 'Remove',
				actionType: 'danger',
				action: (closeDialog) => {
					closeDialog();
					this.$resources.removeDomain.submit({
						name: this.site.name,
						domain: domain
					});
				}
			});
		},
		confirmSetPrimary(domain) {
			this.$confirm({
				title: 'Set as primary',
				message: `Setting as primary will make <b>${domain}</b> the primary URL for your site. Do you want to continue?`,
				actionLabel: 'Set Primary',
				actionType: 'primary',
				action: (closeDialog) => {
					closeDialog();
					this.$resources.setHostName.submit({
						name: this.site.name,
						domain: domain
					});
				}
			});
		}
	}
};
</script>
