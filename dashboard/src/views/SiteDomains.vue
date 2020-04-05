<template>
	<div>
		<section>
			<h2 class="text-lg font-medium">Domains</h2>
			<div v-if="domains.length">
				<p class="text-gray-600">
					Domains pointing to your site
				</p>
				<div
					class="w-full py-4 mt-6 border border-gray-100 rounded shadow sm:w-1/2"
				>
					<div
						class="grid grid-cols-2 px-6 py-3 hover:bg-gray-50"
						v-for="d in domains"
						:key="d.domain"
					>
						<div class="font-semibold">
							{{ d.domain }}
						</div>
						<div>
							<Badge :status="d.status">
								{{ d.status }}
							</Badge>
						</div>
					</div>
				</div>
			</div>
			<div class="text-gray-600" v-else>
				No domains pointing to your site
			</div>
			<div class="mt-4">
				<Button type="primary" @click="showDialog = true">
					Add Domain
				</Button>
			</div>
		</section>
		<Dialog v-model="showDialog" title="Add Domain">
			<p>
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
			<p class="mt-4" v-if="newDomain && !dnsVerified">
				Make a <span class="font-semibold">CNAME</span> record from
				<span class="font-semibold">{{ newDomain }}</span> to
				<span class="font-semibold">{{ site.name }}</span>
			</p>
			<p class="flex mt-4" v-if="dnsVerified === false">
				<FeatherIcon
					name="x"
					class="w-5 h-5 p-1 mr-2 text-red-500 bg-red-100 rounded-full"
				/>
				DNS Verification Failed
			</p>
			<p class="flex mt-4" v-if="dnsVerified === true">
				<FeatherIcon
					name="check"
					class="w-5 h-5 p-1 mr-2 text-green-500 bg-green-100 rounded-full"
				/>
				DNS records successfully verified. Click on Add Domain.
			</p>
			<div slot="actions">
				<Button class="border hover:bg-gray-100" @click="showDialog = false">
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
			domains: [],
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
