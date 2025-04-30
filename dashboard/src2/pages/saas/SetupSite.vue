<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="$resources.saasProduct.loading"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div class="flex h-screen overflow-hidden" v-else>
		<div class="w-full overflow-auto">
			<LoginBox
				v-if="saasProduct"
				title="Set up your site"
				subtitle="It's time to configure your default settings with ease"
				:logo="saasProduct?.logo"
			>
				<template v-slot:logo v-if="saasProduct">
					<div class="flex space-x-2">
						<img
							class="inline-block h-8 w-8 rounded-sm"
							:src="saasProduct?.logo"
						/>
						<!-- <span
							class="select-none text-xl font-semibold tracking-tight text-gray-900"
						>
							{{ saasProduct?.title }}
						</span> -->
					</div>
				</template>
				<template v-slot:default>
					<form class="w-full space-y-4" @submit.prevent="createSite">
						<!-- <div class="w-full space-y-1.5">
							<label class="block text-xs text-ink-gray-5">
								Enter subdomain for your site
							</label>
							<div class="col-span-2 flex w-full">
								<input
									class="dark:[color-scheme:dark] z-10 h-7 w-full rounded rounded-r-none border border-outline-gray-2 bg-surface-white py-1.5 pl-2 pr-2 text-base text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-3 hover:shadow-sm focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
									:placeholder="`${saasProduct.name}-site`"
									v-model="subdomain"
								/>
								<div
									class="flex items-center rounded-r bg-gray-100 px-2 text-base"
								>
									.{{ saasProduct.domain }}
								</div>
							</div>
							<div class="mt-1">
								<div
									v-if="$resources.subdomainExists.loading"
									class="text-sm text-gray-600"
								>
									Checking...
								</div>
								<template
									v-else-if="
										!$resources.subdomainExists.error &&
										$resources.subdomainExists.fetched &&
										subdomain
									"
								>
									<div
										v-if="$resources.subdomainExists.data"
										class="text-sm text-green-600"
									>
										{{ subdomain }}.{{ saasProduct.domain }} is available
									</div>
									<div v-else class="text-sm text-red-600">
										{{ subdomain }}.{{ saasProduct.domain }} is not available
									</div>
								</template>
								<ErrorMessage :message="$resources.subdomainExists.error" />
							</div>
						</div> -->
						<!-- <FormControl
							label="Email address (will be your login ID)"
							:modelValue="$team.doc.user"
							:disabled="true"
							variant="outline"
							class="mb-4"
						/> -->
						<div class="flex gap-2">
							<FormControl
								label="Country"
								class="w-full"
								v-model="country"
								variant="outline"
								type="select"
								:options="countryOptions"
							/>
							<FormControl
								label="Language"
								class="w-full"
								v-model="language"
								variant="outline"
								type="select"
								:options="languageOptions"
							/>
						</div>
						<div class="flex gap-2">
							<FormControl
								class="w-full"
								label="Timezone"
								v-model="timezone"
								variant="outline"
								type="select"
								:options="timezoneOptions"
							/>
							<FormControl
								class="w-full"
								label="Currency"
								v-model="currency"
								variant="outline"
								type="select"
								:options="currencyOptions"
							/>
						</div>
						<ErrorMessage
							class="mt-2"
							:message="$resources.createSite?.error"
						/>
						<Button
							class="mt-8 w-full"
							variant="solid"
							type="submit"
							:loading="findingClosestServer || $resources.createSite?.loading"
							loadingText="Creating site..."
						>
							Next
						</Button>
					</form>
				</template>
				<!-- <template v-slot:footer>
					<div
						class="mt-2 flex w-full items-center justify-center text-sm text-gray-600"
					>
						Powered by Frappe Cloud
					</div>
				</template> -->
			</LoginBox>
		</div>
	</div>
</template>
<script>
import { toast } from 'vue-sonner';
import LoginBox from '../../components/auth/LoginBox.vue';
import dayjs from '../../utils/dayjs';

export default {
	name: 'SignupSetup',
	props: ['productId'],
	components: {
		LoginBox,
	},
	data() {
		return {
			progressErrorCount: 0,
			findingClosestServer: false,
			closestCluster: null,
			timezone: dayjs.tz.guess(),
			currency: null,
			country: null,
			language: null,
			timezoneOptions: [],
			currencyOptions: [],
			countryOptions: [],
			languageOptions: [],
		};
	},
	resources: {
		siteRequest() {
			return {
				url: 'press.api.product_trial.get_request',
				params: {
					product: this.productId,
					account_request: this.$team.doc.account_request,
					timezone: dayjs.tz.guess(),
				},
				auto: true,
				initialData: {},
				onSuccess: (data) => {
					// set options
					const formattedCountry = Object.entries(data.country_info).map(
						([country, details]) => ({
							country: country,
							...details,
						}),
					);
					this.countryOptions = formattedCountry.map((c) => ({
						label: c.country,
						value: c.country,
					}));
					this.currencyOptions = formattedCountry
						.filter((c) => c.currency)
						.map((c) => ({
							label: c.currency_name
								? `${c.currency_name} (${c.currency})`
								: c.currency,
							value: c.currency,
						}))
						// unique by value
						.filter(
							(c, index, self) =>
								index === self.findIndex((t) => t.value === c.value),
						);
					this.timezoneOptions = data.all_timezones.map((tz) => ({
						label: tz,
						value: tz,
					}));
					this.languageOptions = data.languages.map((lang) => ({
						label: lang.language_name,
						value: lang.language_code,
					}));

					// set default values
					this.country = data.country;
					this.currency = formattedCountry.find(
						(c) => c.country === data.country,
					)?.currency;
					this.language = 'en';

					if (data?.status !== 'Pending') {
						this.$router.push({
							name: 'SignupLoginToSite',
							params: { productId: this.productId },
							query: {
								product_trial_request: data.name,
							},
						});
					}
				},
				onError(error) {
					toast.error(error.messages.join('\n'));
				},
			};
		},
		saasProduct() {
			return {
				type: 'document',
				doctype: 'Product Trial',
				name: this.productId,
				auto: true,
			};
		},
		createSite() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams: () => {
					return {
						dt: 'Product Trial Request',
						dn: this.$resources.siteRequest.data.name,
						method: 'create_site',
						args: {
							cluster: this.closestCluster ?? 'Default',
							site_defaults: {
								timezone: this.timezone,
								language: this.language,
								currency: this.currency,
								country: this.country,
							},
						},
					};
				},
				auto: false,
				onSuccess: (data) => {
					this.$router.push({
						name: 'SignupLoginToSite',
						params: { productId: this.productId },
						query: {
							product_trial_request: this.$resources.siteRequest.data.name,
						},
					});
				},
			};
		},
	},
	computed: {
		saasProduct() {
			return this.$resources.saasProduct.doc;
		},
	},
	methods: {
		async createSite() {
			await this.getClosestCluster();
			return this.$resources.createSite.submit();
		},
		async getClosestCluster() {
			if (this.closestCluster) return this.closestCluster;
			let proxyServers = Object.keys(this.saasProduct.proxy_servers);
			if (proxyServers.length > 0) {
				this.findingClosestServer = true;
				let promises = proxyServers.map((server) => this.getPingTime(server));
				let results = await Promise.allSettled(promises);
				let fastestServer = results.reduce((a, b) =>
					a.value.pingTime < b.value.pingTime ? a : b,
				);
				let closestServer = fastestServer.value.server;
				let closestCluster = this.saasProduct.proxy_servers[closestServer];
				if (!this.closestCluster) {
					this.closestCluster = closestCluster;
				}
				this.findingClosestServer = false;
			}
			return this.closestCluster;
		},
		async getPingTime(server) {
			let pingTime = 999999;
			try {
				let t1 = new Date().getTime();
				await fetch(`https://${server}`);
				let t2 = new Date().getTime();
				pingTime = t2 - t1;
			} catch (error) {
				console.warn(error);
			}
			return { server, pingTime };
		},
		redirectToLogin() {
			this.$router.push({
				name: 'Login',
			});
		},
	},
};
</script>
