<template>
	<Button class="font-mono text-xs" :link="link">
		{{ tag }}
	</Button>
</template>

<script>
export default {
	name: 'CommitTag',
	props: ['tag', 'link']
};
</script>
