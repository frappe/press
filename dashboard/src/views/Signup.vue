<template>
	<div class="h-full bg-gray-100 pt-16">
		<div>
			<div class="flex">
				<h1 class="mx-auto font-bold text-2xl px-6 py-4">Frappe Cloud</h1>
			</div>
			<div class="mt-6 mx-auto w-112 py-12 px-12 rounded-md bg-white shadow-lg">
				<div class="mb-8">
					<span class="text-lg">Signup to your account</span>
				</div>
				<form class="flex flex-col" @submit.prevent="login">
					<label class="block">
						<span class="text-gray-800">Full Name</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="text"
							placeholder="John Doe"
						/>
					</label>
					<label class="mt-4 block">
						<span class="text-gray-800">Email</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="email"
							placeholder="johndoe@mail.com"
						/>
					</label>
					<label class="mt-4 block">
						<span class="text-gray-800">Password</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="password"
							placeholder="******"
						/>
					</label>
					<label class="mt-4 block">
						<span class="text-gray-800">Confirm Password</span>
						<input
							class="mt-2 form-input block w-full shadow"
							type="password"
							placeholder="******"
						/>
					</label>
					<span
						v-if="state === 'Login Error'"
						class="mt-2 text-sm text-red-500"
					>
						Invalid email or password
					</span>
					<Button
						class="mt-6 bg-brand focus:bg-blue-600 hover:bg-blue-400 text-white shadow"
						:disabled="state === 'Logging In'"
						:class="{
							'bg-blue-300 cursor-not-allowed': state === 'Logging In'
						}"
						@click="login"
					>
						Signup
					</Button>
					<div class="mt-8 text-center border-t">
						<div class="transform -translate-y-1/2">
							<span class="bg-white px-2 leading-1">
								Or
							</span>
						</div>
					</div>
					<router-link class="text-center text-sm" to="/login">
						Already have an account? Login
					</router-link>
				</form>
			</div>
		</div>
	</div>
</template>
