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
			<Button @click="showDialog = true">
				Add Domain
			</Button>
		</template>
		<div class="divide-y" v-if="domains.data">
			<div v-for="d in domains.data" :key="d.name">
				<div class="flex items-center py-2">
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
					<div class="flex items-center ml-auto space-x-2">
						<Badge v-if="d.status != 'Active' || d.primary" :status="d.status">
							{{ d.primary ? 'Primary' : d.status }}
						</Badge>
						<Button
							@click="retryAddDomain(d.domain)"
							v-if="d.status == 'Broken' && d.retry_count <= 5"
						>
							Retry
						</Button>
						<Dropdown :items="actionItems(d)" right>
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
			</div>
		</div>
		<Dialog v-model="showDialog" title="Add Domain">
			<p class="text-base">
				To add a custom domain, you must already own it. If you don't have one,
				buy it and come back here.
			</p>
			<Input
				type="text"
				class="mt-4"
				placeholder="example.com"
				v-model="newDomain"
				@change="
					dnsVerified = null;
					checkIfExists(newDomain);
				"
			/>
			<p class="mt-4 text-base text-red-600" v-if="domainTaken">
				Domain is already added to
				<span class="font-semibold">{{ domainTaken }}</span>
			</p>
			<p
				class="mt-4 text-base"
				v-if="!domainTaken && newDomain && !dnsVerified"
			>
				Make a <span class="font-semibold">CNAME</span> record from
				<span class="font-semibold">{{ newDomain }}</span> to
				<span class="font-semibold">{{ site.name }}</span>
			</p>
			<p class="flex mt-4 text-base" v-if="dnsVerified === false">
				<FeatherIcon
					name="x"
					class="w-5 h-5 p-1 mr-2 text-red-500 bg-red-100 rounded-full"
				/>
				DNS Verification Failed
			</p>
			<p class="flex mt-4 text-base" v-if="dnsVerified === true">
				<FeatherIcon
					name="check"
					class="w-5 h-5 p-1 mr-2 text-green-500 bg-green-100 rounded-full"
				/>
				DNS records successfully verified. Click on Add Domain.
			</p>
			<div slot="actions">
				<Button @click="showDialog = false">
					Cancel
				</Button>
				<Button
					v-if="!dnsVerified"
					class="ml-3"
					type="primary"
					:disabled="!newDomain || domainTaken || state == 'RequestStarted'"
					@click="checkDNS"
				>
					Verify DNS
				</Button>
				<Button class="ml-3" type="primary" @click="addDomain" v-else>
					Add Domain
				</Button>
			</div>
		</Dialog>
		<Dialog v-model="showRemoveDomainDialog" title="Remove Domain">
			<p class="text-base">
				Are you sure you want to remove this domain?
			</p>
			<p class="mt-4 text-base">
				Please type
				<span class="font-semibold">{{ domainToRemove }}</span> to confirm.
			</p>
			<Input type="text" class="w-full mt-4" v-model="confirmDomainName" />
			<div slot="actions">
				<Button @click="showRemoveDomainDialog = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					type="danger"
					:disabled="domainToRemove !== confirmDomainName"
					@click="removeDomain(domainToRemove)"
				>
					Remove Domain
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
			state: null,
			showDialog: false,
			newDomain: null,
			domainTaken: false,
			dnsVerified: null,
			confirmDomainName: null,
			showRemoveDomainDialog: false,
			domainToRemove: null
		};
	},
	resources: {
		domains() {
			return {
				method: 'press.api.site.domains',
				params: { name: this.site.name }
			};
		}
	},
	mounted() {
		this.$resources.domains.fetch();
	},
	methods: {
		actionItems(domain) {
			return [
				{
					label: 'Remove',
					action: () => {
						this.domainToRemove = domain.domain;
						this.showRemoveDomainDialog = true;
					}
				},
				{
					label: 'Set Primary',
					condition: () => domain.status == 'Active' && !domain.primary,
					action: () => this.setHostName(domain.domain)
				}
			].filter(d => (d.condition ? d.condition() : true));
		},
		async checkDNS() {
			this.dnsVerified = null;
			this.dnsVerified = await this.$call('press.api.site.check_dns', {
				name: this.site.name,
				domain: this.newDomain
			});
		},
		async addDomain() {
			await this.$call('press.api.site.add_domain', {
				name: this.site.name,
				domain: this.newDomain
			});
			this.dnsVerified = false;
			this.showDialog = false;
			this.$resources.domains.fetch();
		},
		async retryAddDomain(domain) {
			await this.$call('press.api.site.retry_add_domain', {
				name: this.site.name,
				domain: domain
			});
			this.$resources.domains.fetch();
		},
		async removeDomain(domain) {
			await this.$call('press.api.site.remove_domain', {
				name: this.site.name,
				domain: domain
			});
			this.showRemoveDomainDialog = false;
			this.domainToRemove = null;
			this.confirmDomainName = null;
			this.$resources.domains.fetch();
		},
		async setHostName(domain) {
			await this.$call('press.api.site.set_host_name', {
				name: this.site.name,
				domain: domain
			});
			this.$resources.domains.fetch();
		},
		async checkIfExists(domain) {
			this.domainTaken = await this.$call('press.api.site.domain_exists', {
				domain
			});
		}
	}
};
</script>
