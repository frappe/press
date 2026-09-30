<template>
	<div
		:id="slugifiedTitle"
		class="group"
		:class="[
			'rounded-md border duration-700 ring-blue-500 flex flex-col',
			shouldHighlight && 'ring-1',
		]"
	>
		<div class="flex items-center border-b p-3 gap-2">
			<h3 class="text-base font-medium text-ink-gray-9">{{ title }}</h3>
			<!-- Grows, so the action slot can push its own content to either edge -->
			<div class="flex flex-1 items-center gap-2">
				<slot name="action"></slot>
			</div>

			<div class="flex items-center gap-2">
				<a
					v-if="docs"
					:href="docs"
					target="_blank"
					rel="noopener"
					title="Read the docs"
					aria-label="Read the docs"
					class="flex items-center text-ink-gray-5 hover:text-ink-gray-8"
				>
					<LucideHelpCircle class="size-3.5" />
				</a>

				<button
					@click="shareCard"
					class="flex items-center gap-1.5"
					aria-label="Copy"
				>
					<LucideLink
						class="size-3 outline-none duration-200 hover:text-current cursor-pointer"
					/>
				</button>
			</div>
		</div>

		<slot></slot>
	</div>
</template>

<script>
import { Tooltip } from 'frappe-ui'

export default {
	name: 'AnalyticsCard',
	props: ['title', 'docs'],
	emits: ['share-card'],
	components: {
		Tooltip,
	},

	data() {
		return {
			shouldHighlight: false,
			_highlightTimeout: null,
		}
	},

	computed: {
		slugifiedTitle() {
			return String(this.title)
				.toLowerCase()
				.trim()
				.replace(/[^a-z0-9]+/g, '-')
				.replace(/^-+|-+$/g, '')
		},
	},

	methods: {
		shareCard() {
			// emit an event to parent to handle sharing
			this.$emit('share-card', this.slugifiedTitle)
		},
	},

	watch: {
		'$route.hash': {
			immediate: true,
			handler(newHash) {
				const slug = newHash?.replace('#', '')
				if (slug === this.slugifiedTitle) {
					this.shouldHighlight = true

					clearTimeout(this._highlightTimeout)
					this._highlightTimeout = setTimeout(() => {
						this.shouldHighlight = false
					}, 1500)
				}
			},
		},
	},
}
</script>
