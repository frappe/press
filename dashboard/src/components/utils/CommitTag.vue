<template>
	<a
		v-if="link"
		:href="link"
		target="_blank"
		:class="[styleClasses, 'hover:bg-gray-200 hover:text-gray-900']"
	>
		<FeatherIcon name="git-commit" class="mr-1 h-4 w-4" />
		{{ tag }}
	</a>
	<span v-else :class="styleClasses">
		<FeatherIcon name="git-commit" class="mr-1 h-4 w-4" />
		{{ tag }}
	</span>
</template>

<script>
export default {
	name: 'CommitTag',
	props: ['tag', 'link'],
	computed: {
		styleClasses() {
			return 'font-mono flex items-center rounded-full bg-gray-100 py-1 px-2 text-xs text-gray-800 font-normal leading-[13px] w-fit';
		}
	}
};
</script>
