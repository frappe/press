<template>
	<Dropdown :items="dropdownOptions" :dropdown-width-full="true">
		<template v-slot="{ toggleDropdown }">
			<button
				class="relative flex items-center justify-between w-full py-1 pl-3 pr-2 text-base leading-5 text-left bg-gray-100 rounded-md select focus:outline-none focus:bg-gray-200"
				@click="toggleDropdown()"
			>
				<div class="flex items-center">
					<img
						class="h-4 mr-2"
						v-if="selectedOption && selectedOption.image"
						:src="selectedOption.image"
						:alt="selectedOption.label"
					/>
					<span v-if="value">{{ selectedOption.label }}</span>
					<span v-else="value" class="text-gray-700">{{ placeholder }}</span>
				</div>

				<svg
					class="right-0 w-5 h-5"
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 20 20"
				>
					<path
						stroke="#98A1A9"
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.5"
						d="M6 8l4 4 4-4"
					/>
				</svg>
			</button>
		</template>
	</Dropdown>
</template>
<script>
export default {
	name: 'RichSelect',
	props: ['options', 'value', 'placeholder'],
	computed: {
		selectedOption() {
			if (!this.value) return null;
			return this.options.find(d => d.value === this.value);
		},
		dropdownOptions() {
			return this.options.map(d => {
				return {
					...d,
					action: () => this.$emit('change', d.value),
					component: {
						render: h => {
							return h(
								'div',
								{
									class: 'flex items-center'
								},
								[
									d.image
										? h('img', { class: 'h-4 mr-2', attrs: { src: d.image } })
										: null,
									h('span', d.label)
								]
							);
						}
					}
				};
			});
		}
	}
};
</script>
