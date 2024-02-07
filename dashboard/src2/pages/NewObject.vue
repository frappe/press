<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs :items="breadcrumbs" />
		</Header>
	</div>
	<div class="mx-auto max-w-4xl px-5">
		<div v-if="options" class="space-y-12 pb-[50vh] pt-12">
			<template v-for="option in options" :key="option.name">
				<div v-if="showOption(option)">
					<div class="flex items-center justify-between">
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							{{ option.label }}
						</h2>
					</div>
					<div class="mt-2">
						<div
							v-if="option?.type === 'region'"
							class="grid grid-cols-2 gap-3 sm:grid-cols-4"
						>
							<button
								v-for="region in optionsData[option.fieldname]"
								:key="region.name"
								:class="[
									vals[option.name] === region.name
										? 'border-gray-900 ring-1 ring-gray-900 hover:bg-gray-100'
										: 'bg-white text-gray-900  ring-gray-200 hover:bg-gray-50',
									'flex w-full items-center rounded border p-3 text-left text-base text-gray-900'
								]"
								@click="vals[option.name] = region.name"
							>
								<div class="flex w-full items-center space-x-2">
									<img :src="region.image" class="h-5 w-5" />
									<span class="text-sm font-medium">
										{{ region.title }}
									</span>
									<Badge
										class="!ml-auto"
										theme="gray"
										v-if="region.beta"
										label="Beta"
									/>
								</div>
							</button>
						</div>
						<div v-else-if="option?.type === 'plan'">
							<NewObjectPlanCards
								:plans="filteredData(option)"
								v-model="vals[option.name]"
							/>
						</div>
						<div v-else-if="option?.type === 'text'">
							<FormControl class="md:w-1/2" v-model="vals[option.name]" />
						</div>
					</div>
				</div>
			</template>
			<div class="md:w-1/2" v-if="showSummaryAndRegionConsent">
				<h2 class="text-base font-medium leading-6 text-gray-900">Summary</h2>
				<div
					class="mt-2 grid gap-x-4 gap-y-2 rounded-md border bg-gray-50 p-4 text-p-base"
					style="grid-template-columns: 3fr 4fr"
				>
					<template v-for="summaryItem in summary">
						<div class="text-gray-600">{{ summaryItem.label }}:</div>
						<div v-html="summaryHTML(summaryItem)"></div>
					</template>
				</div>
			</div>
			<div class="space-y-3 md:w-1/2">
				<FormControl
					v-if="showSummaryAndRegionConsent"
					v-model="vals['agreedToRegionConsent']"
					type="checkbox"
					label="I agree that the laws of the region selected by me shall stand applicable to me and Frappe"
				/>
				<ErrorMessage :message="$resources.createResource.error" />
				<Button
					v-if="showSummaryAndRegionConsent"
					:disabled="!vals.agreedToRegionConsent"
					class="w-full"
					v-bind="primaryAction"
				/>
			</div>
		</div>
	</div>
</template>

<script>
import NewObjectPlanCards from '../components/NewObjectPlanCards.vue';
import Header from '../components/Header.vue';
import { getObject } from '../objects';

export default {
	props: {
		objectType: {
			type: String,
			required: true
		}
	},
	data() {
		return {
			vals: {}
		};
	},
	components: {
		Header,
		NewObjectPlanCards
	},
	resources: {
		optionsData() {
			return { ...this.object.create.optionsResource };
		},
		createResource() {
			return { ...this.object.create.createResource() };
		}
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
		breadcrumbs() {
			return this.object.create.breadcrumbs;
		},
		options() {
			return this.object.create.options;
		},
		summary() {
			return this.object.create.summary;
		},
		optionsData() {
			return this.$resources.optionsData.data;
		},
		primaryAction() {
			if (!this.object.create.primaryAction) return null;
			let props = this.object.create.primaryAction({
				createResource: this.$resources.createResource,
				vals: this.vals
			});
			if (!props) return null;
			return props;
		},
		showSummaryAndRegionConsent() {
			for (let option of this.options) {
				if (!this.showOption(option)) return false;
			}
			return true;
		}
	},
	methods: {
		filteredData(option) {
			if (!option.filter) return this.optionsData[option.fieldname];
			return option.filter(this.optionsData[option.fieldname], this.vals);
		},
		showOption(option) {
			if (!option.dependsOn) return true;
			for (let field of option.dependsOn) {
				if (!this.vals[field]) return false;
			}
			return true;
		},
		summaryHTML(summaryItem) {
			return summaryItem.format
				? summaryItem.format(
						summaryItem.fieldname ? this.vals[summaryItem.fieldname] : this.vals
				  )
				: this.vals[summaryItem.fieldname];
		}
	}
};
</script>
