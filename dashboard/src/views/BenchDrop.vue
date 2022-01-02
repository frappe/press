<template>
	<div class="flex-shrink-0">
		<slot v-bind="{ showDialog }"></slot>
		<Dialog v-model="dialogOpen" title="Drop Bench">
			<p class="text-base">
				Are you sure you want to drop this bench? All the sites on this bench
				should be dropped manually before dropping the bench. This action cannot
				be undone.
			</p>
			<p class="mt-4 text-base">
				Please type
				<span class="font-semibold">{{ bench.title }}</span> to confirm.
			</p>
			<Input type="text" class="w-full mt-4" v-model="confirmBenchName" />
			<ErrorMessage class="mt-2" :error="$resources.dropBench.error" />
			<div slot="actions">
				<Button @click="dialogOpen = false">
					Cancel
				</Button>
				<Button
					class="ml-3"
					type="danger"
					@click="$resources.dropBench.submit()"
					:loading="$resources.dropBench.loading"
				>
					Drop Bench
				</Button>
			</div>
		</Dialog>
	</div>
</template>

<script>
export default {
	name: 'BenchDrop',
	props: ['bench'],
	data() {
		return {
			dialogOpen: false,
			confirmBenchName: null
		};
	},
	resources: {
		dropBench() {
			return {
				method: 'press.api.bench.archive',
				params: {
					name: this.bench.name,
					title: this.bench.title
				},
				onSuccess() {
					this.dialogOpen = false;
					this.$router.push('/sites');
					this.$router.go();
				},
				validate() {
					if (this.bench.title !== this.confirmBenchName) {
						return 'Please type the bench name correctly to confirm';
					}
				}
			};
		}
	},
	methods: {
		showDialog() {
			this.dialogOpen = true;
		}
	}
};
</script>
