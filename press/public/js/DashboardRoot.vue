<template>
<body class="bg-white font-body">
  <div class="flex">
	<div class="w-1/6 bg-gray-900 h-screen flex flex-col justify-between p-4">
	  <div>
		<div class="text-white text-2xl font-bold">Frappe Cloud</div>
		<div class="mt-12">
		  <div class="text-gray-900 py-2 px-3 text-sm bg-gray-500 rounded-sm hover:bg-gray-500 cursor-pointer">
			<router-link :to="{ name: 'site-list' }" tag="div">Sites</router-link>
		  </div>
		  <div class="text-gray-200 py-2 px-3 text-sm hover:bg-gray-500 cursor-pointer">
			<router-link :to="{ name: 'billing-list' }" tag="div">Billing</router-link>
		  </div>
		  <div class="text-gray-200 py-2 px-3 text-sm hover:bg-gray-500 cursor-pointer">
			<router-link :to="{ name: 'payment-list' }" tag="div">Payments</router-link>
		  </div>
		</div>
	  </div>
	  <div class="text-gray-200 py-2 px-3 flex flex-row flex-wrap">
		<i data-feather="settings" class="mr-2 h-5 w-5 self-center"></i> <span class="self-center">Settings</span>
	  </div>
	</div>
	<div class="w-5/6">
	  <div class="h-12 flex justify-between" id="navigation">
		<div></div>
		<div class="self-center mx-4 flex flex-row">
		  <i data-feather="activity" class="mr-3 h-5 w-5 self-center text-gray-500 hover:text-gray-700 cursor-pointer"></i>
		  <i data-feather="bell" class="mr-3 h-5 w-5 self-center text-gray-500 hover:text-gray-700 cursor-pointer"></i>
		  <img class="h-8 w-8 rounded-full ml-2 hover:shadow-md" src="/assets/press/images/user.png">
		</div>
	  </div>
	  <div id="body" class="mx-12">
		<router-view></router-view>
	  </div>
	</div>
  </div>
</body>
</template>

<script>
export default {
	name: "DashboardRoot",
	updated() {
		feather.replace();
	}
};
</script>
