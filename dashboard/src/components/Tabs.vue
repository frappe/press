<template>
	<div>
		<div>
			<ul class="hidden border-b text-base sm:flex">
				<router-link
					v-for="tab in tabs"
					:key="tab.label"
					:to="tab.route"
					v-slot="{ href, navigate, isActive }"
				>
					<li>
						<a
							class="font-base relative mr-6 block truncate border-b px-1 py-4 leading-none focus:outline-none"
							:class="[
								isTabSelected(tab)
									? 'border-brand border-gray-900 text-gray-900'
									: 'border-transparent text-gray-600 hover:text-gray-900'
							]"
							:href="href"
							@click="navigate"
						>
							<span>
								{{ tab.label }}
							</span>
							<div
								class="absolute right-0 top-2 h-2 w-2 rounded-full bg-red-500"
								v-if="tab.showRedDot && !isActive"
							></div>
						</a>
					</li>
				</router-link>
			</ul>
			<select
				class="form-select block w-full sm:hidden"
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
		<div class="w-full py-5">
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
			return this.$route.path.startsWith(tab.route);
		}
	}
};
</script>
