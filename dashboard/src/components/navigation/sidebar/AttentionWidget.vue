<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Button } from 'frappe-ui'

const latestPathName = ref<string | null>(null)
const show = ref(false)

const getLatestMajorBlogPath = async () => {
	const url = '/releases'
	const res = await fetch(url)
	const html = await res.text()

	const tagMatch = html.match(/<a[^>]*data-major="true"[^>]*/)
	const href = tagMatch ? tagMatch[0].match(/href="([^"]+)"/)?.[1] : null

	if (localStorage?.latestReleasePath !== href) {
		latestPathName.value = href
		show.value = true
	}
}

const setLastBlogPathname = () => {
	localStorage.latestReleasePath = latestPathName.value
	show.value = false
}

onMounted(() => {
	getLatestMajorBlogPath()
})

const openUrl = (latestPathName: string | null) => {
  if (!latestPathName) return
  window.open(`https://cloud.frappe.io${latestPathName}`)
}
</script>

<template>
	<div class="mt-auto" />
	<div
		class="hidden md:flex flex-col gap-2 p-3 border border-outline-gray-2 dark:border-outline-gray-1 rounded text-sm bg-surface-white dark:bg-surface-cards hadow mt-auto mb-1"
		v-if="show"
	>
		<div class="flex gap-2">
			<LucidePackageOpen class="size-4 shrink-0" />

			<div class="leading-relaxed -mt-1 mb-2">
				<span class="text-ink-gray-9 font-medium">What's new</span>
				<p class="text-ink-gray-6">Explore our latest updates built for you</p>
			</div>

			<Button variant="ghost" class="-m-2" @click="setLastBlogPathname">
				<LucideX class="size-3.5 shrink-0" />
			</Button>
		</div>

    <Button @click="openUrl">
			New Releases
			<template #suffix>
				<LucideArrowRight class="size-4" />
			</template>
		</Button>
	</div>
</template>
