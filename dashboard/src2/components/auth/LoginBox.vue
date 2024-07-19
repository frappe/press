<template>
	<div class="relative h-full">
		<div class="relative z-10 mx-auto py-8 sm:w-max sm:py-32">
			<div class="flex" @dblclick="redirectForFrappeioAuth">
				<slot name="logo">
					<div class="mx-auto flex items-center space-x-2">
						<BrandLogo type="header" />
						<span
							class="select-none text-xl font-semibold tracking-tight text-gray-900"
						>
							{{ appName }}
						</span>
					</div>
				</slot>
			</div>
			<div
				class="mx-auto w-full bg-white px-4 py-8 sm:mt-6 sm:w-96 sm:rounded-lg sm:px-8 sm:shadow-xl"
			>
				<div class="mb-6 text-center" v-if="title">
					<span
						class="text-center text-lg font-medium leading-5 tracking-tight text-gray-900"
					>
						{{ title }}
					</span>
				</div>
				<slot></slot>
			</div>
		</div>
		<div class="absolute bottom-4 z-[1] flex w-full justify-center">
			<BrandLogo type="footer" />
		</div>
	</div>
</template>

<script>
import BrandLogo from '../BrandLogo.vue';
import { notify } from '@/utils/toast';
import { getBrandInfo } from '../../data/branding';

export default {
	name: 'LoginBox',
	props: ['title', 'logo'],
	components: {
		BrandLogo
	},
	mounted() {
		const params = new URLSearchParams(window.location.search);

		if (params.get('showRemoteLoginError')) {
			notify({
				title: 'Token Invalid or Expired',
				color: 'red',
				icon: 'x'
			});
		}
	},
	methods: {
		redirectForFrappeioAuth() {
			window.location = '/f-login';
		}
	},
	computed: {
		appName() {
			let brandDetails = getBrandInfo();
			return brandDetails.app_name;
		}
	}
};
</script>
