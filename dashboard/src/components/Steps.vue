<template>
	<div>
		<div class="flex items-center justify-center">
			<div class="flex space-x-8">
				<div class="relative" v-for="(step, index) in steps" :key="step.name">
					<div
						class="z-10 flex h-5 w-5 items-center justify-center rounded-full border border-gray-400 bg-white"
						:class="{
							'bg-blue-500 text-white': isStepCompleted(step),
							'border-blue-500': isStepCurrent(step) || isStepCompleted(step)
						}"
					>
						<FeatherIcon
							v-if="isStepCompleted(step)"
							name="check"
							class="h-3 w-3"
							:stroke-width="3"
						/>
						<div
							class="h-1.5 w-1.5 rounded-full bg-blue-500"
							v-if="isStepCurrent(step)"
						></div>
					</div>
					<div
						class="absolute top-1/2 w-8 -translate-x-8 -translate-y-1/2 transform border-t border-gray-400"
						:class="{
							'border-blue-500': isStepCompleted(step) || isStepCurrent(step)
						}"
						v-show="index !== 0"
					></div>
				</div>
			</div>
		</div>
		<template v-if="active">
			<slot v-bind="{ active, next, previous, hasNext, hasPrevious }"></slot>
		</template>
	</div>
</template>
<script>
export default {
	name: 'Steps',
	props: ['steps'],
	data() {
		return {
			active: null
		};
	},
	mounted() {
		this.active = this.steps[0];
	},
	methods: {
		next() {
			if (this.active.validate && !this.active.validate()) {
				return;
			}
			let currentIndex = this.steps.indexOf(this.active);
			let nextIndex = currentIndex + 1;
			if (nextIndex == this.steps.length) {
				nextIndex = this.steps.length - 1;
			}
			let nextStep = this.steps[nextIndex];
			this.active = nextStep;
		},
		previous() {
			let currentIndex = this.steps.indexOf(this.active);
			let prevIndex = currentIndex - 1;
			if (prevIndex == -1) {
				prevIndex = 0;
			}
			this.active = this.steps[prevIndex];
		},
		isStepCompleted(step) {
			let currentIndex = this.steps.indexOf(this.active);
			let stepIndex = this.steps.indexOf(step);
			return stepIndex < currentIndex;
		},
		isStepCurrent(step) {
			return this.active === step;
		}
	},
	computed: {
		hasNext() {
			return this.steps.indexOf(this.active) < this.steps.length - 1;
		},
		hasPrevious() {
			return this.steps.indexOf(this.active) > 0;
		}
	}
};
</script>
