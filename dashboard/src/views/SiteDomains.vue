<template>
	<div>
		<Section
			title="Domains"
			:description="
				domains && domains.length
					? 'Domains pointing to your site'
					: 'No domains pointing to your site'
			"
		>
			<SectionCard v-if="domains && domains.length">
				<div
					class="grid grid-cols-2 px-6 py-3 hover:bg-gray-50"
					v-for="d in domains"
					:key="d.domain"
				>
					<div class="font-semibold">
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
					<div>
						<Badge :status="d.status">
							{{ d.status }}
						</Badge>
					</div>
				</div>
			</SectionCard>
			<div class="mt-4">
				<Button type="primary" @click="showDialog = true">
					Add Domain
				</Button>
			</div>
		</Section>
		<Dialog v-model="showDialog" title="Add Domain">
			<p class="text-base">
				To add a custom domain, you must already own it. If you don't have one,
				buy it and come back here.
			</p>
			<input
				type="text"
				class="w-full mt-4 text-gray-900 form-input"
				placeholder="example.com"
				v-model="newDomain"
				@change="dnsVerified = null"
			/>
			<p class="mt-4 text-base" v-if="newDomain && !dnsVerified">
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
					:disabled="!newDomain || state == 'RequestStarted'"
					@click="checkDNS"
				>
					Verify DNS
				</Button>
				<Button class="ml-3" type="primary" @click="addDomain" v-else>
					Add Domain
				</Button>
			</div>
		</Dialog>
	</div>
</template>

<script>
import Dialog from '@/components/Dialog';
export default {
	name: 'SiteDomains',
	props: ['site'],
	components: {
		Dialog
	},
	data() {
		return {
			state: null,
			showDialog: false,
			domains: null,
			newDomain: null,
			dnsVerified: null
		};
	},
	methods: {
		async fetchDomains() {
			this.domains = await this.$call('press.api.site.domains', {
				name: this.site.name
			});
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
			this.fetchDomains();
		}
	},
	mounted() {
		this.fetchDomains();
	}
};
</script>
