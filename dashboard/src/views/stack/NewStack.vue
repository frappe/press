<template>
	<WizardCard>
		<div>
			<div class="mb-6 text-center">
				<h1 class="text-2xl font-bold sm:text-center">New Stack</h1>
			</div>
			<div v-if="$resources.options.loading" class="flex justify-center">
				<LoadingText />
			</div>
			<div class="space-y-8 sm:space-y-6" v-else>
				<div>
					<label class="text-lg font-semibold mb-2"> Choose a hostname </label>
					<p class="text-base text-gray-700">
						Give your stack a unique name. It can only contain alphanumeric
						characters and dashes.
					</p>
					<div class="mt-3 flex">
						<input
							class="form-input z-10 w-full rounded-r-none"
							type="text"
							v-model="subdomain"
							placeholder="subdomain"
						/>
						<div class="flex items-center rounded-r bg-gray-100 px-4 text-base">
							.{{ $resources.options.data.domain }}
						</div>
					</div>
				</div>
				<div v-if="regionOptions.length > 0">
					<label class="text-lg font-semibold mb-2">Select Region</label>
					<p class="text-base text-gray-700">
						Select the datacenter region where your stack should be created
					</p>
					<div class="mt-3">
						<RichSelect
							:value="selectedRegion"
							@change="selectedRegion = $event"
							:options="regionOptions"
						/>
					</div>
				</div>

				<div class="mt-3">
					<label class="text-lg font-semibold mb-2">Compose file</label>
					<p class="text-base text-gray-700">
						Describe services in your stack using docker compose file
					</p>
					<FormControl
						class="mt-3 h-fit"
						type="textarea"
						placeholder="Paste compose file here..."
						required
						v-model="compose"
					/>
				</div>

				<div class="flex justify-between">
					<div v-if="compose && composeValidated">
						<div class="flex">
							<GreenCheckIcon class="mr-2 w-4" /> Found
							{{ $resources.validateCompose.data.length }} services
						</div>
					</div>
					<ErrorMessage
						class="mb-2"
						:message="$resources.validateCompose.error"
					/>
					<ErrorMessage class="mb-2" :message="$resources.createStack.error" />

					<Button
						v-if="subdomain && compose && !composeValidated"
						variant="solid"
						class="ml-auto"
						:loading="$resources.validateCompose.loading"
						@click="$resources.validateCompose.submit()"
					>
						Validate Compose File
					</Button>
					<Button
						v-if="subdomain && compose && composeValidated"
						variant="solid"
						class="ml-auto"
						:loading="$resources.createStack.loading"
						@click="$resources.createStack.submit()"
					>
						Create Stack
					</Button>
				</div>
			</div>
		</div>
	</WizardCard>
</template>

<script>
import WizardCard from '@/components/WizardCard.vue';
import ServiceSelector from '@/components/ServiceSelector.vue';
import RichSelect from '@/components/RichSelect.vue';
export default {
	name: 'NewStack',
	components: {
		WizardCard,
		ServiceSelector,
		RichSelect
	},
	data() {
		return {
			subdomain: '',
			selectedRegion: null,
			compose: '',
			composeValidated: false
		};
	},
	resources: {
		options() {
			return {
				url: 'press.api.stack.options',
				initialData: {
					clusters: []
				},
				auto: true,
				onSuccess(options) {
					if (!this.selectedRegion) {
						this.selectedRegion = this.options.clusters[0].name;
					}
				}
			};
		},
		createStack() {
			return {
				url: 'press.api.stack.new',
				params: {
					stack: {
						title: `${this.subdomain}.${this.$resources.options.data.domain}`,
						cluster: this.selectedRegion,
						compose: this.compose
					}
				},
				validate() {
					if (!this.subdomain) {
						return 'Subdomain cannot be blank';
					}
					if (!this.compose) {
						return 'Compose file cannot be blank';
					}
				},
				onSuccess(stackName) {
					this.$router.push(`/stacks/${stackName}`);
				}
			};
		},
		validateCompose() {
			return {
				url: 'press.api.stack.validate',
				params: {
					compose: this.compose
				},
				onSuccess(response) {
					if (response?.length > 0) {
						this.composeValidated = true;
					}
				}
			};
		}
	},
	methods: {},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		regionOptions() {
			let clusters = this.options.clusters;
			return clusters.map(d => ({
				label: d.title,
				value: d.name,
				image: d.image
			}));
		}
	}
};
</script>
