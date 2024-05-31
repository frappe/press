<template>
	<Button v-if="$isMobile" @click="showDialog = true">
		<template #icon>
			<i-lucide-filter class="h-4 w-4 text-gray-600" />
		</template>
	</Button>
	<component :is="$isMobile ? 'DialogWrapper' : 'div'" v-bind="wrapperProps">
		<div
			:class="['flex', $isMobile ? 'flex-col gap-y-4' : 'items-center gap-x-2']"
		>
			<template v-for="control in filterControls" :key="control.fieldname">
				<component
					:is="$isMobile || control.type == 'checkbox' ? 'div' : 'Tooltip'"
				>
					<template v-if="!$isMobile" v-slot:body>
						<div
							v-show="control.label && control.value"
							class="mb-1 w-min rounded bg-gray-900 px-2 py-1 text-center text-xs text-white shadow-xl"
						>
							<div class="py-px">
								{{ control.label }}
							</div>
						</div>
					</template>
					<FilterControl
						:label="
							$isMobile || control.type == 'checkbox' ? control.label : null
						"
						:class="control.class"
						:type="control.type"
						:options="control.options"
						:placeholder="
							!$isMobile ? control.placeholder || control.label : null
						"
						:modelValue="control.value"
						@update:modelValue="value => onFilterControlChange(control, value)"
					/>
				</component>
			</template>
		</div>
	</component>
</template>
<script>
import { Tooltip, Dialog } from 'frappe-ui';
import DialogWrapper from './DialogWrapper.vue';
import FilterControl from './FilterControl.vue';

export default {
	name: 'ObjectListFilters',
	props: ['filterControls'],
	emits: ['update:filter'],
	components: {
		Dialog,
		Tooltip,
		DialogWrapper,
		FilterControl
	},
	data() {
		return {
			showDialog: false
		};
	},
	methods: {
		onFilterControlChange(control, value) {
			if (value == '' || value == null) {
				control.value = undefined;
			} else {
				control.value = value;
			}
			this.$emit('update:filter', control);
		}
	},
	computed: {
		wrapperProps() {
			if (!this.$isMobile) {
				return {};
			}
			return {
				modelValue: this.showDialog,
				'onUpdate:modelValue': value => {
					this.showDialog = value;
				},
				options: {
					title: 'Filters'
				}
			};
		}
	}
};
</script>
