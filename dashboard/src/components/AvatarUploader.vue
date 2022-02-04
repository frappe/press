<template>
	<div class="mb-4 flex items-center">
		<Avatar size="lg" :label="label" :imageURL="image" />
		<FileUploader @success="onChange" fileTypes="image/*">
			<template v-slot="{ openFileSelector, uploading, progress, error }">
				<div class="ml-4">
					<Button :loading="uploading" @click="openFileSelector()">
						<span v-if="uploading">Uploading {{ progress }}%</span>
						<span v-else>{{ label }}</span>
					</Button>
					<ErrorMessage class="mt-1" :error="error" />
				</div>
			</template>
		</FileUploader>
	</div>
</template>
<script>
import FileUploader from '@/components/FileUploader.vue';

export default {
	name: 'AvatarUploader',
	components: {
		FileUploader
	},
	props: ['image', 'label'],
	methods: {
		onChange(file) {
			this.$emit('update:image', file.file_url);
		}
	}
};
</script>
