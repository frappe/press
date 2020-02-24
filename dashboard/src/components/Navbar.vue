<template>
	<div class="flex items-center bg-white px-8 py-2 border-b">
		<div class="flex-1">
			<input
				class="focus:outline-none text-sm py-4"
				type="search"
				placeholder="Search"
				name=""
				id=""
			/>
		</div>
		<div>
			<a @click="$store.auth.logout" class="text-sm text-gray-700 hover:text-gray-900 cursor-pointer">Logout</a>
		</div>
	</div>
</template>
