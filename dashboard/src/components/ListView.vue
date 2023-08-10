<template>
	<div
		class="flex h-[16rem] items-center justify-center"
		v-if="groups[0].items.length === 0"
	>
		<div class="text-base text-gray-700">No Items</div>
	</div>
	<div v-for="group in groups" :key="group.group">
		<div
			v-if="group.group"
			class="flex space-x-2 rounded-sm bg-gray-50 px-3 py-1.5"
		>
			<router-link :to="group.link" class="text-base font-medium text-gray-800">
				{{ group.group }}
			</router-link>
			<div class="text-sm text-gray-600">
				{{ group.version }}
			</div>
		</div>
		<div v-for="(item, i) in group.items" class="flex flex-col">
			<div class="flex items-center rounded hover:bg-gray-100">
				<router-link :to="item.link" class="w-full px-3 py-4">
					<div class="flex items-center">
						<div
							class="w-4/12 truncate text-base font-medium"
							:title="item.name"
						>
							{{ item.name }}
						</div>
						<div class="w-2/12">
							<Badge
								class="pointer-events-none"
								variant="subtle"
								:label="item.status"
							/>
						</div>
						<div v-if="item.server_region_info" class="w-2/12">
							<img
								v-if="item.server_region_info.image"
								class="h-4"
								:src="item.server_region_info.image"
								:alt="`Flag of ${item.server_region_info.title}`"
								:title="item.server_region_info.image"
							/>
							<span class="text-base text-gray-700" v-else>
								{{ item.server_region_info.title }}
							</span>
						</div>
						<div v-if="item.version" class="w-2/12">
							<Badge :label="item.version" />
						</div>
						<div class="w-2/12 -space-x-5" v-if="item.tags">
							<Badge
								class="ring-2 ring-white"
								v-for="tag in item.tags.slice(0, 3)"
								:key="tag"
								:label="tag"
							/>
							<Badge
								class="ring-2 ring-white"
								v-if="item.tags.length > 3"
								:label="`+${item.tags.length - 3}`"
							/>
						</div>
						<div v-if="item.plan" class="w-1/12">
							<div class="text-base text-gray-700">
								{{ item.plan ? `${$planTitle(item.plan)}/mo` : 'No Plan Set' }}
							</div>
						</div>
						<div
							v-if="
								item.number_of_sites !== undefined &&
								item.number_of_apps !== undefined
							"
							class="mt-1 hidden w-2/12 text-sm text-gray-600 sm:block"
						>
							{{
								`${item.number_of_sites} ${$plural(
									item.number_of_sites,
									'Site',
									'Sites'
								)}`
							}}
							&middot;
							{{
								`${item.number_of_apps} ${$plural(
									item.number_of_apps,
									'App',
									'Apps'
								)}`
							}}
						</div>
					</div>
				</router-link>
				<Dropdown :options="dropdownItems(item)">
					<template v-slot="{ open }">
						<Button variant="ghost" class="mr-2" icon="more-horizontal" />
					</template>
				</Dropdown>
			</div>

			<div v-if="i < group.items.length - 1" class="mx-2.5 border-b" />
		</div>
	</div>
</template>
<script>
export default {
	name: 'ListView',
	props: {
		items: {
			default: []
		},
		dropdownItems: {
			type: Function
		}
	},
	computed: {
		groups() {
			return this.items[0]?.group
				? this.items
				: [{ group: '', items: this.items }];
		}
	}
};
</script>
