<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs
				:items="[
					{ label: 'Clusters', route: '/clusters' },
					{ label: 'New Cluster', route: '/clusters/new' }
				]"
			/>
		</Header>
	</div>
	<div class="mx-auto max-w-2xl">
		<div v-if="options" class="space-y-12 pb-[50vh] pt-12">
			<div class="flex flex-col">
				<h2 class="text-sm font-medium leading-6 text-gray-900">
					Choose Cluster Provider
				</h2>
				<div class="mt-2 w-full space-y-2">
					<div class="grid grid-cols-2 gap-3">
						<button
							v-for="c in options?.cloud_providers"
							:key="c.name"
							@click="cloudProvider = c.name"
							:class="[
								cloudProvider === c.name
									? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
									: 'border-gray-400 bg-white text-gray-900 ring-gray-200 hover:bg-gray-50',
								'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
							]"
						>
							<div class="flex w-full items-center justify-between space-x-2">
								<span class="text-sm font-medium">
									{{ c.title }}
								</span>
							</div>
						</button>
					</div>
				</div>
			</div>
			<div v-if="cloudProvider">
				<div class="flex flex-col">
					<h2 class="text-sm font-medium text-gray-900">Enter Cluster Name</h2>
					<div class="mt-2">
						<FormControl
							v-model="clusterTitle"
							type="text"
							class="block rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
						/>
					</div>
				</div>
				<div class="flex flex-col mt-4">
					<h2 class="text-sm font-medium text-gray-900">Description</h2>
					<div class="mt-2">
						<FormControl
							v-model="clusterDescription"
							type="text"
							class="block rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
						/>
					</div>
				</div>
				<div class="flex flex-col mt-4">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Select Region
					</h2>
					<div class="mt-1">
						<FormControl
							v-model="clusterRegion"
							type="select"
							:options="options?.regions[cloudProvider]"
							class="block rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
						/>
					</div>
				</div>
				<div class="flex flex-col mt-4">
					<h2 class="text-sm font-medium leading-6 text-gray-900">
						Availability Zone
					</h2>
					<div class="mt-1">
						<FormControl
							v-model="clusterAvailabilityZone"
							type="text"
							class="block rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
						/>
					</div>
				</div>
				<div v-if="clusterRegion && clusterTitle">
					<div
						v-if="cloudProvider == 'AWS EC2'"
						class="flex flex-col space-y-2 mt-4"
					>
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							Enter AWS Credentials
						</h2>
						<div class="flex space-x-3">
							<FormControl
								class="w-full"
								v-model="awsAccessKeyId"
								label="AWS Access Key"
								type="text"
							/>
							<FormControl
								class="w-full"
								v-model="awsSecretAccessKey"
								label="AWS Secret Access Key"
								type="text"
							/>
						</div>
					</div>
					<div
						v-if="cloudProvider == 'OCI'"
						class="flex flex-col space-y-2 mt-4"
					>
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							Enter OCI Credentials
						</h2>
						<div class="flex space-x-3">
							<FormControl
								class="w-full"
								v-model="ociUser"
								label="OCI User"
								type="text"
							/>
							<FormControl
								class="w-full"
								v-model="ociTenancy"
								label="OCI Tenancy"
								type="text"
							/>
						</div>
						<div class="flex space-x-3">
							<FormControl
								class="w-full"
								v-model="ociPrivateKey"
								label="OCI Private Key"
								type="textarea"
							/>
							<FormControl
								class="w-full"
								v-model="ociPublicKey"
								label="OCI Public Key"
								type="textarea"
							/>
						</div>
					</div>
				</div>
				<div v-if="clusterRegion && clusterTitle">
					<div class="flex flex-col space-y-2 mt-4">
						<div class="flex w-full items-center justify-between space-x-2">
							<h2 class="text-sm font-medium leading-6 text-gray-900">
								Enter CIDR Block
							</h2>
							<Tooltip :text="cidrDesc">
								<i-lucide-info class="h-4 w-4 text-gray-500" />
							</Tooltip>
						</div>
						<div class="mt-2">
							<TextInput
								class="w-full block rounded-md border-gray-300 shadow-sm focus:border-gray-900 focus:ring-gray-900 sm:text-sm"
								label="Determine the starting IP and the size of your VPC using CIDR notation"
								:debounce="500"
								v-model="cidrBlock"
							>
								<template #suffix>
									<span class="text-sm text-gray-500" v-if="cidrBlock">
										{{ maxIPsCount }}
									</span>
								</template>
							</TextInput>
						</div>
					</div>
				</div>
			</div>
			<Summary
				:options="summaryOptions"
				v-if="
					clusterTitle &&
					clusterRegion &&
					cidrBlock &&
					((cloudProvider === 'AWS EC2' &&
						awsAccessKeyId &&
						awsSecretAccessKey) ||
						(cloudProvider === 'OCI' &&
							ociUser &&
							ociTenancy &&
							ociPublicKey &&
							ociPrivateKey))
				"
			>
			</Summary>

			<div
				class="flex flex-col space-y-4"
				v-if="
					clusterTitle &&
					clusterRegion &&
					cidrBlock &&
					((cloudProvider === 'AWS EC2' &&
						awsAccessKeyId &&
						awsSecretAccessKey) ||
						(cloudProvider === 'OCI' &&
							ociUser &&
							ociTenancy &&
							ociPublicKey &&
							ociPrivateKey))
				"
			>
				<FormControl
					type="checkbox"
					v-model="agreedToRegionConsent"
					:label="`I agree that the laws of the region selected by me shall stand applicable to me and Frappe.`"
				/>
				<ErrorMessage class="my-2" :message="$resources.createCluster.error" />
				<Button
					variant="solid"
					:disabled="!agreedToRegionConsent"
					@click="
						$resources.createCluster.submit({
							cluster: {
								title: clusterTitle,
								description: clusterDescription,
								cloud_provider: cloudProvider,
								region: clusterRegion,
								availability_zone: clusterAvailabilityZone,
								cidr_block: cidrBlock,
								aws_access_key_id: awsAccessKeyId,
								aws_secret_access_key: awsSecretAccessKey,
								oci_user: ociUser,
								oci_tenancy: ociTenancy,
								oci_public_key: ociPublicKey,
								oci_private_key: ociPrivateKey
							}
						})
					"
					:loading="$resources.createCluster.loading"
				>
					Create Cluster
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import Header from '../components/Header.vue';
import Summary from '../components/Summary.vue';

export default {
	name: 'NewCluster',
	components: {
		Header,
		Summary
	},
	data() {
		return {
			clusterTitle: '',
			clusterRegion: '',
			clusterDescription: '',
			cloudProvider: '',
			awsAccessKeyId: '',
			awsSecretAccessKey: '',
			ociUser: '',
			ociTenancy: '',
			ociPublicKey: '',
			ociPrivateKey: '',
			clusterAvailabilityZone: '',
			maxIPsCount: '',
			cidrBlock: '',
			cloudProviderOptions: [],
			agreedToRegionConsent: false,
			cidrDesc:
				'You must specify an IPv4 address range for your VPC. \nSpecify the IPv4 address range as a Classless Inter-Domain Routing (CIDR) block; \nfor example, 10.0.0.0/16. A CIDR block size must be between a /16 netmask and /28 netmask.'
		};
	},
	watch: {
		cloudProvider() {
			this.clusterRegion = '';
			this.awsAccessKeyId = '';
			this.awsSecretAccessKey = '';
			this.ociUser = '';
			this.ociTenancy = '';
			this.ociPublicKey = '';
			this.ociPrivateKey = '';
			this.cidrBlock = '';
			this.clusterAvailabilityZone = '';
		},

		cidrBlock() {
			let _maxIPsCount =
				Math.pow(2, 32 - parseInt(this.cidrBlock.split('/')[1])) - 2;

			this.maxIPsCount = isNaN(_maxIPsCount) ? '' : _maxIPsCount + ' IPs';
		}
	},
	resources: {
		options() {
			return {
				url: 'press.api.cluster.options',
				auto: true,
				transform: data => {
					return {
						regions: data.regions,
						cloud_providers: data.cloud_providers
					};
				}
			};
		},
		createCluster() {
			return {
				url: 'press.api.cluster.new',
				validate({ cluster }) {
					if (!cluster.title) {
						return 'Cluster name is required';
					} else if (!cluster.region) {
						return 'Please select a region';
					} else if (!cluster.availability_zone) {
						return 'Please select an availability zone';
					} else if (!cluster.cidr_block) {
						return 'Please specify a CIDR block';
					} else if (cluster.cidr_block) {
						let range = parseInt(cluster.cidr_block.split('/')[1]);
						if (!range || range < 16 || range > 28) {
							return 'Invalid CIDR block. A CIDR block size must be between a /16 netmask and /28 netmask.';
						}
					} else if (
						cluster.cloud_provider == 'AWS EC2' &&
						(!cluster.aws_access_key_id || !cluster.aws_secret_access_key)
					) {
						return 'Please enter AWS credentials';
					} else if (
						cluster.cloud_provider == 'OCI' &&
						(!cluster.oci_user ||
							!cluster.oci_tenancy ||
							!cluster.oci_public_key ||
							!cluster.oci_private_key)
					) {
						return 'Please enter OCI credentials';
					}
				},
				onSuccess(cluster) {
					this.$router.push({
						name: 'Cluster Detail Overview',
						params: { name: cluster.name }
					});
				}
			};
		}
	},
	computed: {
		options() {
			return this.$resources.options.data;
		},
		summaryOptions() {
			return [
				{
					label: 'Cloud Provider',
					value: this.cloudProvider
				},
				{
					label: 'Cluster Title',
					value: this.clusterTitle
				},
				{
					label: 'Cluster Region',
					value: this.clusterRegion
				},
				{
					label: 'Availability Zone',
					value: this.clusterAvailabilityZone
				},
				{
					label: 'CIDR Block',
					value: this.cidrBlock
				},
				{
					label: 'AWS Access Key',
					value: this.awsAccessKeyId,
					condition: () => this.awsAccessKeyId
				},
				{
					label: 'AWS Secret Access Key',
					value: this.awsSecretAccessKey,
					condition: () => this.awsSecretAccessKey
				},
				{
					label: 'OCI User',
					value: this.ociUser,
					condition: () => this.ociUser
				},
				{
					label: 'OCI Tenancy',
					value: this.ociTenancy,
					condition: () => this.ociTenancy
				}
			];
		}
	}
};
</script>
