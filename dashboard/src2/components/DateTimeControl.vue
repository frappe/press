<template>
	<div class="flex items-center space-x-1">
		<FormControl
			class="w-52"
			:label="label ? label : 'Date'"
			type="select"
			variant="outline"
			:options="dayOptions"
			v-model="scheduledDate"
		/>
		<FormControl
			class="w-24"
			:class="label ? 'mt-5' : ''"
			:label="label ? '' : 'Hour'"
			type="select"
			variant="outline"
			:options="hourOptions"
			v-model="scheduledHour"
		/>
		<FormControl
			class="w-24"
			:class="label ? 'mt-5' : ''"
			:label="label ? '' : 'Minute'"
			type="select"
			variant="outline"
			:options="minuteOptions"
			v-model="scheduledMinute"
		/>
	</div>
</template>

<script>
import dayjs from '../utils/dayjs';

export default {
	props: ['modelValue', 'label'],
	emits: ['update:modelValue'],
	data() {
		return {
			scheduledDate: this.modelValue ? this.modelValue.split('T')[0] : '',
			scheduledHour: this.modelValue
				? this.modelValue.split('T')[1].split(':')[0]
				: '',
			scheduledMinute: this.modelValue
				? this.modelValue.split('T')[1].split(':')[1]
				: ''
		};
	},
	watch: {
		scheduledTime() {
			this.$emit('update:modelValue', this.scheduledTime);
		}
	},
	computed: {
		dayOptions() {
			let days = [];
			for (let i = 0; i < 7; i++) {
				days.push({
					label: dayjs().add(i, 'day').format('dddd, MMMM D'),
					value: dayjs().add(i, 'day').format('YYYY-MM-DD')
				});
			}
		},
		hourOptions() {
			let options = [...Array(24).keys()].map(n => ({
				label:
					n < 12
						? `${(n == 0 ? 12 : n).toString().padStart(2, '0')} AM`
						: `${(n != 12 ? n - 12 : n).toString().padStart(2, '0')} PM`,
				value: n
			}));

			if (this.scheduledDate === dayjs().format('YYYY-MM-DD')) {
				options = options.filter(
					option =>
						option.value >=
						(dayjs().minute() < 45 ? dayjs().hour() : dayjs().hour() + 1)
				);
			}

			return options;
		},
		minuteOptions() {
			let options = [0, 15, 30, 45].map(i => ({
				label: i.toString().padStart(2, '0'),
				value: i
			}));

			if (
				this.scheduledDate === dayjs().format('YYYY-MM-DD') &&
				this.scheduledHour === String(dayjs().hour())
			) {
				options = options.filter(option => option.value >= dayjs().minute());
			}

			return options;
		},
		scheduledTime() {
			if (!this.scheduledDate || !this.scheduledHour || !this.scheduledMinute)
				return null;

			return dayjs(
				`${this.scheduledDate} ${this.scheduledHour}:${this.scheduledMinute}`
			).format('YYYY-MM-DDTHH:mm');
		}
	}
};
</script>
