<template>
	<nav class="border-b bg-white">
		<div class="z-10 mx-auto md:container">
			<div class="flex h-16 items-center justify-between px-4 sm:px-8">
				<FrappeSaasLogo @dblclick="redirectToSaasHome" />

				<div class="flex items-center">
					<Button class="ml-2" icon-left="life-buoy" link="/support"
						>Support</Button
					>
					<div class="relative ml-3">
						<div>
							<div class="relative ml-3">
								<Dropdown :items="dropdownItems" right>
									<template v-slot="{ toggleDropdown }">
										<button
											class="focus:shadow-solid flex max-w-xs items-center rounded-full text-sm text-white focus:outline-none"
											id="user-menu"
											aria-label="User menu"
											aria-haspopup="true"
											@click="toggleDropdown()"
										>
											<Avatar
												v-if="$account.user"
												:label="$account.user.first_name"
												:imageURL="$account.user.user_image"
											/>
										</button>
									</template>
								</Dropdown>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</nav>
</template>

<script>
import FrappeSaasLogo from '@/components/FrappeSaasLogo.vue';
export default {
	name: 'SaasNavbar',
	components: {
		FrappeSaasLogo
	},
	data() {
		return {
			mobileMenuOpen: false,
			dropdownItems: [
				{
					label: 'Settings',
					action: () => this.$router.push('/saas/setting')
				},
				{
					label: 'Logout',
					action: () => this.$auth.logout()
				}
			]
		};
	},
	resources: {
		apps() {
			return {
				method: 'press.api.saas.get_apps',
				onSuccess(r) {
					console.log(r);
				}
			};
		}
	},
	methods: {
		redirectToSaasHome() {
			window.location = '/saas/upgrade';
		}
	}
};
</script>
