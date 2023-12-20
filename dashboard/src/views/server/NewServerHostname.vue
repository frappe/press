<template>
	<div>
		<label class="text-lg font-semibold"> Choose a name for your server </label>
		<p class="text-base text-gray-700">
			Name your server based on its purpose. For e.g., Personal Websites,
			Staging Server, etc.
		</p>
		<div class="mt-4 flex">
			<FormControl
				class="w-full"
				:value="title"
				@change="titleChange"
				placeholder="Server"
			/>
		</div>
		<div class="mt-6 space-y-1">
			<h2 class="text-lg font-semibold">Select Region</h2>
			<p class="text-base text-gray-700">
				Select the datacenter region where your server should be created
			</p>
			<div class="mt-1">
				<RichSelect
					:value="selectedRegion"
					@change="$emit('update:selectedRegion', $event)"
					:options="regionOptions"
				/>
			</div>
		</div>
		<div class="mt-4">
			<ErrorMessage :message="errorMessage" />
		</div>
	</div>
</template>
<script>
import RichSelect from '@/components/RichSelect.vue';

export default {
	name: 'Hostname',
	props: ['options', 'title', 'selectedRegion'],
	emits: ['update:title', 'error', 'update:selectedRegion'],
	data() {
		return {
			errorMessage: null
		};
	},
	components: {
		RichSelect
	},
	computed: {
		regionOptions() {
			return this.options.regions.map(d => ({
				label: d.title,
				value: d.name,
				image: d.image,
				beta: d.beta
			}));
		}
	},
	async mounted() {
		if (this.regionOptions.length == 1) {
			this.$emit('update:selectedRegion', this.regionOptions[0].value);
		}
	},
	methods: {
		async titleChange(e) {
			let title = e.target.value;
			this.$emit('update:title', title);
			let error = this.validateTitle(title);
			this.errorMessage = error;
			this.$emit('error', error);
		},
		validateTitle(title) {
			if (!title) {
				return 'Server name cannot be left blank';
			}
			return null;
		}
	}
};
</script>
