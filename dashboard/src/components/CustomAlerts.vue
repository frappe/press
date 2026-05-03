<template>
	<div v-if="localBanners.length > 0" :class="containerClass ?? ``">
		<AlertBanner
			v-for="banner in localBanners"
			:key="banner.name"
			:class="disableLastChildBottomMargin ? `mb-5 last:mb-0` : `mb-5`"
			:title="`<b>${banner.title}:</b> ${banner.message}`"
			:type="banner.type.toLowerCase()"
			:isDismissible="banner.is_dismissible"
			@dismissBanner="closeBanner(banner.name)"
		>
			<template v-if="!!banner.help_url">
				<Button
					class="ml-auto flex flex-row items-center gap-1"
					@click="openHelp(banner.help_url)"
					variant="outline"
				>
					Open help
					<lucide-external-link class="inline h-4 w-3 pb-0.5" />
				</Button>
			</template>
		</AlertBanner>
	</div>
</template>

<script>
import AlertBanner from '../components/AlertBanner.vue';

export default {
	name: 'CustomAlerts',
	components: { AlertBanner },
	props: {
		ctx_type: {
			type: String,
			required: false,
			validator: (value) => !value || ['Site', 'Server'].includes(value),
		},
		ctx_name: {
			required: false,
			validator: (value) =>
				!value ||
				(typeof value === 'string' && value.length > 0) ||
				(Array.isArray(value) &&
					value.every((el) => typeof el === 'string') &&
					value.length > 0),
		},
		containerClass: {
			type: String,
			required: false,
			default: '',
		},
		disableLastChildBottomMargin: {
			type: Boolean,
			required: false,
			default: false,
		},
	},
	data() {
		return {
			localBanners: [],
			localDismissedBanners: {},
		};
	},
	computed: {
		ctxNames() {
			return Array.isArray(this.ctx_name)
				? this.ctx_name
				: this.ctx_name
					? [this.ctx_name]
					: [];
		},
	},
	methods: {
		closeBanner(bannerName) {
			const banner = this.localBanners.find((b) => b.name === bannerName);
			if (!banner) return;

			this.localBanners = this.localBanners.filter(
				(b) => b.name !== bannerName,
			);

			if (banner.is_global || banner.type_of_scope == 'Cluster') {
				// Persist dismissal to local storage
				this.localDismissedBanners[bannerName] = Date.now();
				localStorage.setItem(
					'dismissed_banners',
					JSON.stringify(this.localDismissedBanners),
				);
			} else {
				// Optimistic dismissal to DB
				this.$resources.dismissBanner.submit({ banner_name: bannerName });
			}
		},
		openHelp(url) {
			window.open(url, '_blank');
		},
		trimOldDismissedBanners() {
			// Remove dismissed banners older than 60 days from local storage
			const SIXTY_DAYS_IN_MS = 60 * 24 * 60 * 60 * 1000;
			const now = Date.now();
			let diff = false;

			for (const [bannerName, timestamp] of Object.entries(
				this.localDismissedBanners,
			)) {
				if (now - timestamp > SIXTY_DAYS_IN_MS) {
					delete this.localDismissedBanners[bannerName];
					diff = true;
				}
			}

			if (diff) {
				localStorage.setItem(
					'dismissed_banners',
					JSON.stringify(this.localDismissedBanners),
				);
			}
		},
		isRelevantBanner(banner) {
			if (banner.is_global) return true;

			const ctxMatches = (list) =>
				Array.isArray(list) &&
				list.some((item) => this.ctxNames.includes(item));

			switch (this.ctx_type) {
				case 'Server':
					return (
						(banner.type_of_scope === 'Server' && ctxMatches(banner.server)) ||
						(banner.type_of_scope === 'Cluster' && ctxMatches(banner.cluster))
					);

				case 'Site':
					return (
						(banner.type_of_scope === 'Site' && ctxMatches(banner.site)) ||
						(banner.type_of_scope === 'Server' && ctxMatches(banner.server)) ||
						(banner.type_of_scope === 'Cluster' && ctxMatches(banner.cluster))
					);

				case 'List Page':
					return ['Team', 'Cluster', 'Server'].includes(banner.type_of_scope);

				default:
					return true;
			}
		},
	},
	resources: {
		banners() {
			return {
				url: 'press.api.account.get_user_banners',
				auto: !!this.$team?.doc,
				onSuccess: (data) => {
					try {
						const parsed = JSON.parse(
							localStorage.getItem('dismissed_banners') || '{}',
						);
						// Ensure parsed is an object
						this.localDismissedBanners =
							parsed && typeof parsed === 'object' && !Array.isArray(parsed)
								? parsed
								: {};
					} catch {
						this.localDismissedBanners = {};
					}

					this.trimOldDismissedBanners();

					this.localBanners = data
						.filter(this.isRelevantBanner)
						.filter((banner) => !(banner.name in this.localDismissedBanners));
				},
			};
		},
		dismissBanner() {
			return { url: 'press.api.account.dismiss_banner' };
		},
	},
};
</script>
