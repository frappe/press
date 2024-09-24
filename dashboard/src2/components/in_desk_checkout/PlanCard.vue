<template>
	<button
		class="flex flex-col overflow-hidden rounded border text-left hover:bg-gray-50"
		:class="{
			'border-gray-900 ring-1 ring-gray-900': selected,
			'border-gray-300': !selected,
			'pointer-events-none opacity-50': plan.disabled
		}"
		@click="$emit('select')"
	>
		<div
			class="w-full border-b p-3"
			:class="{
				'border-gray-900 ring-1 ring-gray-900': selected
			}"
		>
			<div class="flex items-center justify-between">
				<div class="text-lg">
					<span class="font-medium text-gray-900">
						{{ plan?.label ?? '' }}
					</span>
				</div>
			</div>
			<div class="mt-1 text-sm text-gray-600">
				{{ plan?.sublabel ?? '' }}
			</div>
		</div>
		<div class="p-3 text-p-sm text-gray-800">
			<div v-for="feature in plan.features">
				<div v-if="feature.value" class="flex space-x-2">
					<component
						v-if="feature.icon"
						:is="_icon(feature.icon, 'mt-1 h-3 w-4 shrink-0 text-gray-900')"
					/>
					<span>{{ feature?.value ?? "" }} </span>
					<span class="ml-1 text-gray-600">
						{{ feature?.label ?? "" }}
					</span>
				</div>
			</div>
		</div>
	</button>
</template>

<script>
import { icon } from '../../utils/components';

export default {
	props: ['plan', 'selected'],
	methods: {
		_icon(iconName, classes) {
			return icon(iconName, classes);
		}
	},
	emits: ['select']
};
</script>
