<template>
	<div>
		{{ message }}
		{{ props }}
	</div>
</template>
<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps({ bench: String });
const message = ref('still to be built');
</script>
