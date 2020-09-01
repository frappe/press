<template>
	<Layout>
		<div class="px-4 sm:px-8">
			<div class="pt-20 pb-12 text-center">
				<h1 class="text-6xl font-bold text-gray-900">
					One Click Custom Apps for your Frappe Sites
				</h1>
				<p class="max-w-lg mx-auto mt-4 text-gray-600">
					Extend functionality of your Frappe sites by finding an app
					that suits you and install it in a few steps.
				</p>
				<div
					class="relative inline-flex items-center justify-center mt-6"
				>
					<FeatherIcon
						name="search"
						class="absolute top-0 left-0 w-4 h-4 mt-1.5 ml-2"
					/>
					<input
						class="pl-8 placeholder-gray-500 form-input w-96 focus:bg-white focus:shadow-outline-gray"
						type="search"
						placeholder="Search for apps"
					/>
				</div>
			</div>

			<div class="pb-36">
				<h2 class="text-4xl font-bold sr-only">Apps</h2>
				<a class="grid grid-cols-4 gap-8 mt-8">
					<div
						class="p-6 border border-gray-100 rounded-lg shadow cursor-pointer hover:shadow-lg"
						v-for="app in apps"
						:key="app.name"
					>
						<img
							class="w-10 h-10 border border-gray-200 rounded-full"
							:src="app.image"
						/>
						<h3 class="mt-4 font-semibold">{{ app.name }}</h3>
						<p class="mt-2 text-base text-gray-600 line-clamp">
							{{ app.description }}
						</p>
					</div>
				</a>
			</div>
		</div>
	</Layout>
</template>

<script>
import Button from 'dashboard/src/components/global/Button';
import FeatherIcon from 'dashboard/src/components/global/FeatherIcon';

export default {
	metaInfo: {
		title: 'Marketplace'
	},
	components: {
		Button,
		FeatherIcon
	},
	computed: {
		apps() {
			return this.$page.apps.edges.map(e => e.node);
		}
	}
};
</script>

<page-query>
query {
  apps: allFrappeApps {
    edges {
      node {
        id
        name
		description
		image
      }
    }
  }
}
</page-query>
