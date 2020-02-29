<template>
	<div class="rounded-full overflow-hidden" :class="sizeClasses">
		<img
			v-if="imageURL"
			:src="imageURL"
			class="object-cover"
			:class="sizeClasses"
		/>
		<div
			v-else
			class="bg-green-200 text-green-800 flex h-full items-center justify-center w-full uppercase"
			:class="{ sm: 'text-xs', md: 'text-base', lg: 'text-lg' }[size]"
		>
			{{ label && label[0] }}
		</div>
	</div>
</template>

<script>
export default {
	name: 'Avatar',
	props: {
		imageURL: String,
		label: String,
		size: {
			default: 'md'
		}
	},
	computed: {
		sizeClasses() {
			return {
				sm: 'w-4 h-4',
				md: 'w-8 h-8',
				lg: 'w-12 h-12'
			}[this.size];
		}
	}
};
</script>
