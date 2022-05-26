<template>
	<Dropdown :items="dropdownOptions" :dropdown-width-full="true">
		<template v-slot="{ toggleDropdown }">
			<button
				class="select relative flex w-full items-center justify-between rounded-md bg-gray-100 py-1 pl-3 pr-2 text-left text-base leading-5 focus:bg-gray-200 focus:outline-none"
				@click="toggleDropdown()"
			>
				<div class="flex items-center">
					<img
						class="mr-2 h-4"
						v-if="selectedOption && selectedOption.image"
						:src="selectedOption.image"
						:alt="selectedOption.label"
					/>
					<span v-if="value">{{ selectedOption.label }}</span>
					<span v-else-if="placeholder" class="text-gray-700">
						{{ placeholder }}
					</span>
				</div>

				<svg
					class="right-0 h-5 w-5"
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
import { h } from 'vue';
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
					component: this.getDropdownItemComponent(d)
				};
			});
		}
	},
	methods: {
		getDropdownItemComponent(option) {
			return {
				render: () => {
					return h(
						'div',
						{
							class: 'flex items-center'
						},
						[
							option.image
								? h('img', {
										class: ['h-4 mr-2', this.$attrs.class],
										src: option.image
								  })
								: null,
							h('span', option.label)
						]
					);
				}
			};
		}
	}
};
</script>
