<template>
	<div class="my-2 max-h-96 overflow-auto">
		<div
			v-for="(group, index) in groups"
			:key="group.name"
			@click="$emit('update:selectedGroup', group)"
			class="focus-within:shadow-outline flex cursor-pointer border px-4 py-3 text-left text-base"
			:class="[
				selectedGroup === group ? 'bg-blue-50' : 'hover:bg-blue-50',
				{
					'border-b-0':
						groups.length > 1 && ![groups.length - 1, 0].includes(index),
					'rounded-b-md': groups.length > 1 && index === groups.length - 1,
					'rounded-t-md border-b-0': groups.length > 1 && index === 0,
					'rounded-md border': groups.length == 1
				}
			]"
		>
			<div class="flex flex-row items-center gap-2">
				<input type="radio" :checked="selectedGroup === group" />
				<div class="group-select text-lg font-medium text-gray-900">
					{{ group.title }}
				</div>
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'ChangeGroupSelector',
	props: ['groups', 'selectedGroup'],
	emits: ['update:selectedGroup']
};
</script>
