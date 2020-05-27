<template>
	<div>
		<div>
			<ul class="hidden overflow-x-auto text-sm border-b sm:flex">
				<router-link
					v-for="tab in tabs"
					:key="tab.label"
					:to="tab.route"
					v-slot="{ href, route, navigate, isActive }"
				>
					<li>
						<a
							class="block px-1 py-4 mr-8 font-medium leading-none truncate border-b border-transparent focus:outline-none"
							:class="[
								isActive
									? 'border-brand text-brand'
									: 'text-gray-800 hover:text-gray-900'
							]"
							:href="href"
							@click="navigate"
						>
							{{ tab.label }}
						</a>
					</li>
				</router-link>
			</ul>
			<select
				class="block w-full sm:hidden form-select"
				@change="e => changeTab(e.target.value)"
			>
				<option
					v-for="tab in tabs"
					:selected="isTabSelected(tab)"
					:value="tab.route"
					:key="tab.label"
				>
					{{ tab.label }}
				</option>
			</select>
		</div>
		<div class="w-full pt-6 sm:pt-10">
			<slot></slot>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Tabs',
	props: ['tabs'],
	methods: {
		changeTab(route) {
			this.$router.replace(route);
		},
		isTabSelected(tab) {
			return this.$route.path.endsWith(tab.route);
		}
	}
};
</script>
