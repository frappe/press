<template>
	<Card
		title="Versions"
		subtitle="Deployed versions of your bench"
		:loading="$resources.versions.loading"
		v-if="$resources.versions.data && $resources.versions.data.length"
	>
		<template #actions>
			<router-link
				class="text-base text-blue-500 hover:text-blue-600"
				:to="`/benches/${bench.name}/sites`"
			>
				View versions →
			</router-link>
		</template>
		<div class="z-10 divide-y">
			<ListItem
				v-for="version in $resources.versions.data"
				:key="version.name"
				:title="version.name"
				:subtitle="
					// prettier-ignore
					version.status == 'Broken'
						? 'Contact support to resolve this issue'
						: version.deployed_on
							? formatDate(version.deployed_on, 'DATETIME_FULL')
							: null
				"
			>
				<template #actions>
					<div class="flex items-center space-x-2">
						<Badge v-if="version.status != 'Active'" :status="version.status" />
						<router-link
							v-else
							class="block"
							:to="`/benches/${bench.name}/sites/${version.name}`"
						>
							<Badge class="cursor-pointer hover:text-green-600" color="green">
								{{ version.sites.length }}
								{{ $plural(version.sites.length, 'site', 'sites') }}
							</Badge>
						</router-link>
					</div>
				</template>
			</ListItem>
		</div>
	</Card>
</template>
<script>
export default {
	name: 'BenchOverviewVersions',
	props: ['bench'],
	resources: {
		versions() {
			return {
				method: 'press.api.bench.versions',
				params: { name: this.bench.name },
				auto: true
			};
		}
	}
};
</script>
