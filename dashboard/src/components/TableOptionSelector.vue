<template>
	<div v-if="options.length">
		<div
			class="flex px-4 py-3 text-base text-gray-800 border border-b-0 bg-gray-0 rounded-t-md"
		>
			<div class="w-10"></div>
			<div class="w-1/4" v-for="d in header" :key="d.fieldname">
				{{ d.label }}
			</div>
		</div>
		<div
			class="flex px-4 py-3 text-base text-left border border-b-0 cursor-pointer focus-within:shadow-outline"
			:class="[
				selectedOption === option ? 'bg-blue-50' : 'hover:bg-blue-50',
				{
					'border-b rounded-b-md': i === options.length - 1,
					'pointer-events-none': option.disabled
				}
			]"
			v-for="(option, i) in options"
			:key="option.name"
			@click="$emit('change', option)"
		>
			<div class="flex items-center w-10">
				<input
					type="radio"
					class="form-radio"
					:checked="selectedOption === option"
					@change="e => (selectedOption = e.target.checked ? option : null)"
				/>
			</div>
			<div
				class="w-1/4 text-gray-900"
				:class="{ 'opacity-25': option.disabled, 'font-semibold': j == 0 }"
				v-for="(d, j) in header"
				:key="d.fieldname"
			>
				{{ option[d.fieldname] }}
			</div>
		</div>
	</div>
	<div class="text-center" v-else>
		<Button :loading="true">Loading</Button>
	</div>
</template>

<script>
export default {
	name: 'SitePlansTable',
	props: ['options', 'header', 'selectedOption'],
	model: {
		prop: 'selectedOption',
		event: 'change'
	}
};
</script>
