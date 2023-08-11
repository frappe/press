<template>
	<div class="min-w-full">
		<slot :rows="rows" :columns="columns" />
	</div>
</template>

<script>
export default {
	name: 'Table',
	props: {
		columns: Array,
		rows: Array
	},
	provide() {
		return {
			columns: this._columns,
			rows: this.rows
		};
	},
	computed: {
		_columns() {
			return this.columns.map(column => {
				return {
					...column,
					width: column.width || 1,
					name: column.name
				};
			});
		},
		$rows() {
			return this.rows;
		}
	}
};
</script>
