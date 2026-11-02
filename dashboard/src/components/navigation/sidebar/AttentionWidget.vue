<script setup lang="ts">
import { Button, createResource } from 'frappe-ui'
import { computed, ref } from 'vue'

const dismissed = ref(false)

const latestBlog = createResource({
	url: 'press.api.blog.latest_blog',
	auto: true,
})

const show = computed(() => !dismissed.value && latestBlog.data?.show)

const markRead = createResource({ url: 'press.api.blog.mark_read' })

const dismiss = () => {
	dismissed.value = true
	markRead.submit({ blog: latestBlog.data.url })
}

const openBlog = () => {
	window.open(latestBlog.data.url)
	dismissed.value = true
	markRead.submit({ blog: latestBlog.data.url })
}
</script>

<template>

	<div
		class="fade-in hidden md:flex flex-col p-3 rounded text-sm bg-surface-white dark:bg-surface-cards shadow-md mb-1"
		v-if="show"
	>
		<div class="flex gap-2">
			<LucidePackageOpen class="size-4 shrink-0" />

			<div class="leading-relaxed -mt-1 mb-3">
				<span class="text-ink-gray-9 font-medium">What's new</span>
				<p class="text-ink-gray-6 text-p-sm">{{ latestBlog.data.title }}</p>
			</div>

			<Button variant="ghost" class="-m-2" @click="dismiss">
				<LucideX class="size-3.5 shrink-0" />
			</Button>
		</div>

		<Button @click="openBlog">
			Check out
			<template #suffix>
				<LucideArrowRight class="size-4" />
			</template>
		</Button>
	</div>
</template>
