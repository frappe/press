<template>
	<Popover class="w-full">
		<template #target="{ togglePopover }">
			<Button
				class="font-mono text-xs"
				:label="modelValue?.label || 'Select'"
				icon-right="chevron-down"
				@click="togglePopover"
			/>
		</template>
		<template #body="{ isOpen, togglePopover }">
			<div
				v-if="isOpen"
				@vue:mounted="focusSearch()"
				class="relative mt-1 rounded-lg bg-surface-modal text-base shadow-2xl"
			>
				<div
					class="max-h-[15rem] w-[clamp(0px,50vw,40rem)] overflow-y-auto px-1.5 pb-1.5 pt-1.5"
				>
					<FormControl
						ref="searchInput"
						class="mt-0.5 mb-1"
						type="search"
						placeholder="Search releases..."
						:modelValue="searchQuery"
						@update:model-value="
							(val) => {
								searchQuery = val;
								onQueryChange();
							}
						"
					/>

					<div
						v-if="!searchQuery.length"
						class="text-xs font-medium text-gray-500 py-2 pl-2"
					>
						Recent
					</div>

					<!-- displayedOptions ideally contains query results when searchQuery is non-empty. It is populated with options prop otherwise. -->
					<!-- In both the above cases, displayedOptions may be empty if there are no releases created. -->

					<div
						v-for="option in displayedOptions"
						:key="option.value"
						@click="!option.isYanked && selectOption(option, togglePopover)"
						class="flex cursor-pointer items-center justify-between rounded px-2.5 py-1.5 text-base hover:bg-gray-50"
						:class="{
							'bg-surface-gray-3': isSelected(option),
							'opacity-50 cursor-not-allowed': option.isYanked,
						}"
					>
						<div class="flex flex-1 gap-2 overflow-hidden items-center">
							<div class="flex flex-shrink-0">
								<svg
									v-if="isSelected(option)"
									class="h-4 w-4 text-ink-gray-7"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M5 13l4 4L19 7"
									></path>
								</svg>
								<div v-else class="h-4 w-4" />
							</div>
							<span
								:title="option.timestamp"
								class="flex-1 truncate text-ink-gray-7"
							>
								{{ option.label }}
							</span>
							<span
								v-if="option.isYanked"
								class="text-xs text-red-500 font-medium"
							>
								Blacklisted
							</span>
						</div>
					</div>
					<div class="*:text-center *:mb-2 *:mt-3 *:text-xs *:text-gray-400">
						<div v-if="$resources.releases.loading && !!searchQuery.length">
							Searching...
						</div>
						<div v-else-if="!displayedOptions.length">No results found</div>
					</div>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script>
import { Popover, Button, debounce } from 'frappe-ui';
import FormControl from 'frappe-ui/src/components/FormControl/FormControl.vue';
import { nextTick } from 'vue';

export default {
	name: 'CommitChooser',
	components: {
		Popover,
		Button,
	},
	data() {
		return {
			searchQuery: '',
			queryResult: [],
		};
	},
	props: [
		'options',
		'modelValue',
		'app',
		'source',
		'currentRelease',
		'isYanked',
	],
	emits: ['update:modelValue'],
	methods: {
		selectOption(option, togglePopover) {
			this.$emit('update:modelValue', {
				label: this.isVersion(option.label)
					? option.label
					: option.label.match(/\((\w+)\)$/)?.[1] || option.label,
				value: option.value,
				hash: option.hash,
				timestamp: option.timestamp,
			});
			togglePopover();
		},
		isSelected(option) {
			return this.modelValue?.value === option.value;
		},
		isVersion(tag) {
			return tag.match(/^v\d+\.\d+\.\d+$/);
		},
		onQueryChange() {
			debounce(() => {
				this.$resources.releases.reload();
			}, 300)();
		},
		focusSearch() {
			nextTick(() => {
				// Focus the input element inside popover FormControl
				const el = this.$refs.searchInput?.$el?.querySelector('input');
				el?.focus();
			});
		},
	},
	resources: {
		releases() {
			return {
				url: 'press.api.bench.search_releases',
				params: {
					app: this.app,
					source: this.source,
					query: this.searchQuery?.trim(),
					fields: ['name', 'message', 'timestamp', 'hash'],
					current_release: this.currentRelease,
					limit: 20,
				},
				initialData: [],
				transform: (data) => {
					return data.map((release) => ({
						label: release.message,
						value: release.name,
						timestamp: release.timestamp,
						hash: release.hash,
					}));
				},
			};
		},
	},
	computed: {
		displayedOptions() {
			return this.searchQuery.length
				? this.$resources.releases.data
				: this.options;
		},
	},
	watch: {
		searchQuery(newQuery) {
			if (newQuery.length === 0) {
				this.queryResult = [];
				return;
			}
		},
	},
};
</script>
