<template>
	<div class="mt-2">
		<div
			v-if="option?.type === 'card'"
			class="grid grid-cols-2 gap-3 sm:grid-cols-4"
		>
			<button
				v-for="card in filteredData(option)"
				:key="card.name"
				:class="[
					vals[option.name] === card.name
						? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
						: 'bg-white text-gray-900  ring-gray-200 hover:bg-gray-50',
					'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
				]"
				@click="vals[option.name] = card.name"
			>
				<div class="flex w-full items-center space-x-2">
					<img v-if="card.image" :src="card.image" class="h-5 w-5" />
					<span class="text-sm font-medium">
						{{ card.title || card.name }}
					</span>
					<span v-if="card.status" class="!ml-auto text-gray-600">
						{{ card.status }}
					</span>
					<Badge class="!ml-auto" theme="gray" v-if="card.beta" label="Beta" />
				</div>
			</button>
		</div>
		<div v-else-if="option?.type === 'plan'">
			<NewObjectPlanCards
				:plans="filteredData(option)"
				v-model="vals[option.name]"
			/>
		</div>
		<div class="md:w-1/2" v-else-if="option?.type === 'text'">
			<FormControl v-model="vals[option.name]" :type="option.type" />
		</div>
		<div v-else-if="option?.type === 'Component'">
			<component
				v-memo="[option]"
				:is="option.component({ optionsData, vals })"
				v-model="vals[option.name]"
			/>
		</div>
	</div>
</template>

<script>
import NewObjectPlanCards from './NewObjectPlanCards.vue';

export default {
	props: ['option', 'optionsData', 'modelValue'],
	emits: ['update:modelValue'],
	components: {
		NewObjectPlanCards
	},
	data() {
		return {
			vals: this.modelValue
		};
	},
	watch: {
		vals: {
			handler(newVals) {
				this.$emit('update:modelValue', newVals);
			}
		}
	},
	methods: {
		filteredData(option) {
			if (!option.filter) return this.optionsData[option.fieldname];
			return option.filter(
				this.optionsData[option.fieldname],
				this.vals,
				this.optionsData
			);
		}
	}
};
</script>
