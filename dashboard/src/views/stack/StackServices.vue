<template>
	<div class="space-y-5">
		<Card
			title="Services"
			subtitle="Services available on your stack"
			:loading="$resources.services.loading"
		>
			<div class="max-h-96 divide-y">
				<ListItem
					v-for="service in $resources.services.data"
					:key="service.name"
					:title="service.title"
				>
					<template #subtitle>
						<div class="mt-1 flex items-center space-x-2 text-gray-600">
							<FeatherIcon name="git-branch" class="h-4 w-4" />
							<div class="truncate text-base hover:text-clip">
								{{ service.image }}:{{ service.tag }}
							</div>
						</div>
					</template>
					<template #actions>
						<div class="ml-auto flex items-center space-x-2">
							<Badge
								v-if="!service.deployed"
								label="Not Deployed"
								theme="orange"
							/>
							<Dropdown :options="dropdownItems(service)" right>
								<template v-slot="{ open }">
									<Button icon="more-horizontal" />
								</template>
							</Dropdown>
						</div>
					</template>
				</ListItem>
			</div>
		</Card>
	</div>
</template>
<script>
export default {
	name: 'StackServices',
	props: ['stackName', 'stack'],
	resources: {
		services() {
			return {
				url: 'press.api.stack.services',
				params: {
					name: this.stackName
				},
				auto: true
			};
		}
	},
	methods: {
		dropdownItems(service) {
			return [
				{
					label: 'Visit Repo',
					onClick: () => window.open(`https://${service.image}`, '_blank')
				}
			].filter(Boolean);
		}
	}
};
</script>
