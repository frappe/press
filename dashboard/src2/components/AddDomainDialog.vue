<template>
	<Dialog
		v-model="showDialog"
		:modelValue="true"
		:options="{ title: 'Add Domain' }"
	>
		<template v-slot:body-content>
			<div class="space-y-4">
				<p class="text-p-base">
					To add a custom domain, you must already own it. If you don't have
					one, buy it and come back here.
				</p>
				<FormControl
					placeholder="www.example.com"
					v-model="newDomain"
					:readonly="dnsVerified"
					autocomplete="off"
				/>

				<div
					v-if="newDomain && !dnsVerified"
					class="prose prose-sm space-y-2 prose-strong:text-gray-800"
				>
					<p>Create one of the following DNS records:</p>
					<ul>
						<li>
							<strong>CNAME</strong> record from
							<strong>{{ newDomain }}</strong>
							to
							<strong>{{ site.name }}</strong>
						</li>
						<li>
							<strong>A</strong> record from
							<strong>{{ newDomain }}</strong>
							to
							<strong>{{ site.inbound_ip }}</strong>
						</li>
					</ul>
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

		<template #actions>
			<Button
				v-if="!dnsVerified"
				class="mt-2 w-full"
				variant="solid"
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
				class="mt-2 w-full"
				variant="solid"
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
</template>
<script>
export default {
	name: 'AddDomainDialog',
	props: {
		site: {
			type: Object,
			required: true
		}
	},
	emits: ['domainAdded'],
	data() {
		return {
			showDialog: true,
			newDomain: null
		};
	},
	resources: {
		checkDNS: {
			url: 'press.api.site.check_dns',
			validate() {
				if (!this.newDomain) return 'Domain cannot be empty';
			}
		},
		addDomain: {
			url: 'press.api.site.add_domain',
			onSuccess() {
				this.$resources.checkDNS.reset();
				this.$emit('domainAdded');
				this.showDialog = false;
			}
		},
		retryAddDomain: {
			url: 'press.api.site.retry_add_domain',
			onSuccess() {
				this.$emit('domainAdded');
				// this.$resources.domains.fetch();
			}
		}
	},
	computed: {
		dnsVerified() {
			return this.dnsResult?.matched;
		},
		dnsResult() {
			return this.$resources.checkDNS.data;
		}
	}
};
</script>
