<template>
	<div
		:id="slugifiedTitle"
		class="group"
		:class="[
			'rounded-md border duration-700 ring-blue-500',
			shouldHighlight && 'ring-1',
		]"
	>
		<div class="flex h-12 items-center justify-between border-b px-5 gap-2">
			<div class="flex items-center">
				<h3 class="text-lg font-medium text-gray-900">{{ title }}</h3>
				<div class="pl-2">
					<Tooltip text="Share Link to this Card">
						<CopyIcon
							class="h-4 text-gray-600 outline-none duration-200 hover:text-current cursor-pointer"
							@click="shareCard"
						/>
					</Tooltip>
				</div>
			</div>

			<slot name="action"></slot>
		</div>
		<slot></slot>
	</div>
</template>

<script>
import { Tooltip } from 'frappe-ui';
import { icon } from '../../utils/components';

export default {
	name: 'AnalyticsCard',
	props: ['title'],
	emits: ['share-card'],
	components: {
		Tooltip,
		CopyIcon: icon('link'),
	},

	data() {
		return {
			shouldHighlight: false,
			_highlightTimeout: null,
		};
	},

	computed: {
		slugifiedTitle() {
			return String(this.title)
				.toLowerCase()
				.trim()
				.replace(/[^a-z0-9]+/g, '-')
				.replace(/^-+|-+$/g, '');
		},
	},

	methods: {
		shareCard() {
			// emit an event to parent to handle sharing
			this.$emit('share-card', this.slugifiedTitle);
		},
	},

	watch: {
		'$route.hash': {
			immediate: true,
			handler(newHash) {
				const slug = newHash?.replace('#', '');
				if (slug === this.slugifiedTitle) {
					this.shouldHighlight = true;

					clearTimeout(this._highlightTimeout);
					this._highlightTimeout = setTimeout(() => {
						this.shouldHighlight = false;
					}, 1500);
				}
			},
		},
	},
};
</script>
