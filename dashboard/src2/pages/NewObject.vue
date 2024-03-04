<template>
	<div class="sticky top-0 z-10 shrink-0">
		<Header>
			<Breadcrumbs :items="breadcrumbs" />
		</Header>
	</div>
	<div class="mx-auto max-w-4xl px-5">
		<div
			v-if="$resources.optionsData.loading"
			class="py-4 text-base text-gray-600"
		>
			Loading...
		</div>
		<div v-else-if="options" class="space-y-12 pb-[50vh] pt-12">
			<template v-for="option in options" :key="option.name">
				<div v-if="showOption(option)">
					<div class="flex items-center justify-between">
						<h2 class="text-sm font-medium leading-6 text-gray-900">
							{{ option.label }}
						</h2>
						<template v-if="option?.labelSlot">
							<component :is="option.labelSlot({ optionsData })" />
						</template>
					</div>
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
									<Badge
										class="!ml-auto"
										theme="gray"
										v-if="card.beta"
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
						<div
							class="col-span-2 flex md:w-1/2"
							v-else-if="option?.type === 'text'"
						>
							<TextInput
								class="w-full"
								:class="option.class"
								v-model="vals[option.name]"
							/>
							<template v-if="option?.slot">
								<component :is="option.slot({ optionsData })" />
							</template>
						</div>
						<div v-else-if="option?.type === 'Component'">
							<component
								v-once
								:is="option.component({ optionsData, vals })"
								v-model="vals[option.name]"
							/>
						</div>
					</div>
				</div>
			</template>

			<div class="md:w-2/3" v-if="showSummaryAndRegionConsent">
				<h2 class="text-base font-medium leading-6 text-gray-900">Summary</h2>
				<div
					class="mt-2 grid gap-x-4 gap-y-2 rounded-md border bg-gray-50 p-4 text-p-base"
					style="grid-template-columns: 1fr 1fr"
				>
					<template v-for="summaryItem in summary">
						<div v-if="summaryItemHTML(summaryItem)" class="text-gray-600">
							{{ summaryItem.label }}:
						</div>
						<div
							v-if="summaryItemHTML(summaryItem)"
							v-html="summaryItemHTML(summaryItem)"
						/>
					</template>
				</div>
			</div>
			<div class="flex flex-col space-y-3">
				<FormControl
					v-if="showSummaryAndRegionConsent"
					v-model="vals['agreedToRegionConsent']"
					type="checkbox"
					label="I agree that the laws of the region selected by me shall stand applicable to me and Frappe"
				/>
				<FormControl
					v-for="consent in consents"
					v-if="showSummaryAndRegionConsent"
					v-model="vals[consent.name]"
					type="checkbox"
					:label="consent.label"
				/>
				<ErrorMessage :message="$resources.createResource.error" />
				<Button
					v-if="showSummaryAndRegionConsent"
					:disabled="!vals.agreedToRegionConsent"
					class="md:w-1/2"
					v-bind="primaryAction"
					:loading="$resources.createResource.loading"
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
		},
		// router passed object name for secondary create
		// eg: /benches/:name/sites/new'
		name: {
			type: String,
			required: false
		}
	},
	data() {
		return {
			vals: {}
		};
	},
	mounted() {
		if (this.name) this.vals[this.secondaryCreate.propName] = this.name;
	},
	components: {
		Header,
		NewObjectPlanCards
	},
	resources: {
		optionsData() {
			return {
				...this.object.create.optionsResource({ routerProp: this.name })
			};
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
			if (this.secondaryCreate?.routeName === this.$route.name) {
				let isObjectServer = Object.keys(this.vals)[0] === 'server';
				let objectName = Object.values(this.vals)[0];

				return [
					{
						label: isObjectServer ? 'Servers' : 'Benches',
						route: isObjectServer ? '/servers' : '/benches'
					},
					{
						label: objectName,
						route: {
							name: isObjectServer
								? 'Server Detail Benches'
								: 'Release Group Detail Sites',
							params: { name: objectName }
						}
					},
					{
						label: this.object.create.title,
						route: this.$route.path
					}
				];
			}
			return [
				{ label: this.object.list.title, route: this.object.list.route },
				{
					label: this.object.create.title,
					route: this.object.create.route
				}
			];
		},
		secondaryCreate() {
			return this.object.create.secondaryCreate || null;
		},
		options() {
			let options = this.object.create.options;
			if (
				this.secondaryCreate &&
				this.$route.name === this.secondaryCreate.routeName
			) {
				options = options.filter(
					option => !this.secondaryCreate.optionalFields.includes(option.name)
				);
			}
			return options;
		},
		summary() {
			return this.object.create.summary.filter(
				summaryItem => !summaryItem.hideWhen || !this.vals[summaryItem.hideWhen]
			);
		},
		consents() {
			return this.object.create.consents;
		},
		optionsData() {
			return this.$resources.optionsData.data;
		},
		primaryAction() {
			if (!this.object.create.primaryAction) return null;
			let props = this.object.create.primaryAction({
				createResource: this.$resources.createResource,
				vals: this.vals,
				optionsData: this.optionsData
			});
			if (!props) return null;
			return props;
		},
		showSummaryAndRegionConsent() {
			for (let option of this.options) {
				if (!this.showOption(option)) return false;
			}
			for (let summaryItem of this.summary) {
				if (
					!summaryItem.optional &&
					summaryItem.fieldname &&
					!this.vals[summaryItem.fieldname]
				)
					return false;
			}

			return true;
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
		},
		showOption(option) {
			if (!option.dependsOn) return true;
			for (let field of option.dependsOn) {
				if (!this.vals[field]) {
					if (
						this.secondaryCreate?.routeName === this.$route.name &&
						this.secondaryCreate.optionalFields.includes(field)
					)
						return true;
					else return false;
				}
			}
			return true;
		},
		summaryItemHTML(summaryItem) {
			return summaryItem.format
				? summaryItem.format(
						summaryItem.fieldname
							? this.vals[summaryItem.fieldname]
							: this.vals,
						this.optionsData
				  )
				: this.vals[summaryItem.fieldname];
		}
	}
};
</script>
