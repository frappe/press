<template>
	<div v-if="localBanners.length > 0" :class="containerClass ?? ``">
		<AlertBanner
			v-for="banner in localBanners"
			:class="disableLastChildBottomMargin ? `mb-5 last:mb-0` : `mb-5`"
			:key="banner.name"
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
	components: {
		AlertBanner,
	},
	props: {
		ctx_type: {
			type: String,
			required: false,
			validator: (value) => !value || ['Site', 'Server'].includes(value),
		},
		ctx_name: {
			type: String,
			required: false,
			validator: (value) =>
				!value || (typeof value === 'string' && value.length > 0),
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
		};
	},
	methods: {
		closeBanner(bannerName) {
			this.localBanners = this.localBanners.filter(
				(b) => b.name !== bannerName,
			);
			this.$resources.dismissBanner.submit({
				banner_name: bannerName,
			});
		},
		openHelp(url) {
			window.open(url, '_blank');
		},
	},
	resources: {
		banners() {
			return {
				url: 'press.api.account.get_user_banners',
				auto: !!this.$team?.doc,
				onSuccess: (data) => {
					this.localBanners =
						this.ctx_type === 'Server'
							? data.filter(
									(banner) =>
										banner.server === this.ctx_name || banner.is_global,
								)
							: this.ctx_type === 'Site'
								? data.filter(
										(banner) =>
											banner.site === this.ctx_name || banner.is_global,
									)
								: data;
				},
			};
		},
		dismissBanner() {
			return {
				url: 'press.api.account.dismiss_banner',
			};
		},
	},
};
</script>
