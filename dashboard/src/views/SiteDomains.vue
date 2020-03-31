<template>
	<div>
		<section>
			<h2 class="font-medium text-lg">Domains</h2>
			<div v-if="domains.length">
				<p class="text-gray-600">
					Domains pointing to your site
				</p>
				<div
					class="w-full sm:w-1/2 mt-6 border border-gray-100 shadow rounded py-4"
				>
					<div class="px-6 py-3 hover:bg-gray-50" v-for="d in domains">
						<div>
							{{ d.domain }}
						</div>
					</div>
				</div>
			</div>
			<div class="text-gray-600" v-else>
				No domains pointing to your site
			</div>

			<div class="mt-4">
				<Button
					class="bg-brand hover:bg-blue-600 text-white"
					@click="showModal=true"
				>
					Add Domain
				</Button>
			</div>
		</section>
		<Modal :show="showModal" @hide="showModal = false">
			<div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
				<div class="sm:flex sm:items-start">
					<div class="mt-3 sm:mt-0 sm:text-left">
						<h3 class="text-xl leading-6 font-medium text-gray-900">
							Add Domain
						</h3>
						<div class="mt-4 leading-5 text-gray-800">
							<p>
								Domain
							</p>
							<input
								type="text"
								class="mt-4 form-input text-gray-900 w-full"
								v-model="newDomain"
								@change="dnsVerified=false"
							/>
							<p class="mt-4" v-if="newDomain && !dnsVerified">
								Make a <span class="font-semibold">CNAME</span> 
								record from <span class="font-semibold">{{ newDomain }}</span> 
								to <span class="font-semibold">{{site.name}}</span>
							</p>
						</div>
					</div>
				</div>
			</div>
			<div class="p-4 sm:px-6 sm:py-4 flex items-center justify-end">
				<span class="flex rounded-md shadow-sm">
					<Button class="border hover:bg-gray-100" @click="showModal = false">
						Cancel
					</Button>
				</span>
				<span class="flex rounded-md shadow-sm ml-3" v-if="!dnsVerified">
					<Button
						class="bg-brand hover:bg-blue-600 text-white"
						:disabled="!newDomain"
						@click="checkDNS"
					>
						Verify DNS
					</Button>
				</span>
				<span class="flex rounded-md shadow-sm ml-3" v-else>
					<Button
						class="bg-brand hover:bg-blue-600 text-white"
						@click="addDomain"
					>
						Add Domain
					</Button>
				</span>
			</div>
		</Modal>
	</div>
</template>

<script>
import Modal from '@/components/Modal';
export default {
	name: 'SiteDomains',
	props: ['site'],
	components: {
		Modal
	},
	data() {
		return {
			showModal: false,
			domains: [],
			newDomain: null,
			dnsVerified: false,
		};
	},
	methods: {
		async fetchDomains() {
			this.domains = await this.$call('press.api.site.domains', {
				name: this.site.name
			});
		},
		async checkDNS() {
			this.dnsVerified = await this.$call('press.api.site.check_dns', {
				name: this.site.name,
				domain: this.newDomain,
			});
		},
		async addDomain() {
			await this.$call('press.api.site.add_domain', {
				name: this.site.name,
				domain: this.newDomain,
			});
			this.dnsVerified = false;
			this.showModal = false;
			this.fetchDomains();
		},
	},
	mounted() {
		this.fetchDomains();
	},
};
</script>
