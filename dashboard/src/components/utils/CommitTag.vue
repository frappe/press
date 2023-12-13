<template>
	<a
		v-if="link"
		:href="link"
		target="_blank"
		:class="[styleClasses, 'hover:bg-gray-200 hover:text-gray-900']"
	>
		{{ tag }}
	</a>
	<span v-else :class="styleClasses">
		{{ tag }}
	</span>
</template>

<script>
export default {
	name: 'CommitTag',
	props: ['tag', 'link'],
	computed: {
		styleClasses() {
			return 'h-7 font-mono flex items-center rounded-full bg-gray-100 py-1 px-2 text-xs text-gray-800 font-normal leading-[13px] w-fit';
		}
	}
};
</script>
