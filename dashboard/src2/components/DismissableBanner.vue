<template>
	<AlertBanner v-if="show" :title="title" :type="type">
		<slot></slot>
		<Button class="ml-1" variant="ghost" @click="dismiss">
			<template #icon>
				<i-lucide-x class="h-4 w-4" />
			</template>
		</Button>
	</AlertBanner>
</template>

<script>
import AlertBanner from './AlertBanner.vue';

export default {
	props: {
		title: String,
		id: {
			type: String,
			required: true,
		},
		type: {
			type: String,
		},
	},
	data() {
		return {
			_show: true,
		};
	},
	components: { AlertBanner },
	computed: {
		show: {
			get() {
				if (!this._show) return false;

				const dismissedDate = parseInt(
					localStorage.getItem(`dismissed-banner-${this.id}`),
				);
				if (!dismissedDate) return true;

				const currentDate = Date.now();
				const diff = currentDate - dismissedDate;

				// 7 days
				if (diff > 1000 * 60 * 60 * 24 * 7) return true;

				return false;
			},
			set(value) {
				this._show = value;
			},
		},
	},
	methods: {
		dismiss() {
			this.show = false;
			localStorage.setItem(`dismissed-banner-${this.id}`, Date.now());
		},
	},
};
</script>
