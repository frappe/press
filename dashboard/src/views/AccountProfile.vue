<template>
	<div>
		<section>
			<h2 class="text-lg font-medium">Profile</h2>
			<p class="text-gray-600">Your profile information</p>
			<div class="w-full mt-6 text-sm sm:w-1/2">
				<div>
					<span class="text-gray-800">Photo</span>
					<div class="flex items-center mt-2">
						<Avatar
							size="lg"
							:label="account.user.first_name"
							:imageURL="account.user.user_image"
						/>
						<input
							ref="userImage"
							type="file"
							accept="image/*"
							class="hidden"
							@change="onUserImage"
						/>
						<Button
							class="ml-4"
							:disabled="uploading"
							@click="$refs.userImage.click()"
						>
							<span v-if="uploading">
								Uploading {{ Math.floor((uploaded / total) * 100) }}%
							</span>
							<span v-else>Change</span>
						</Button>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-4 mt-4 sm:grid-cols-2">
					<label class="block">
						<span class="text-gray-800">First Name</span>
						<input
							class="block w-full mt-2 shadow form-input"
							type="text"
							v-model="account.user.first_name"
						/>
					</label>
					<label class="block">
						<span class="text-gray-800">Last Name</span>
						<input
							class="block w-full mt-2 shadow form-input"
							type="text"
							v-model="account.user.last_name"
						/>
					</label>
				</div>
				<label class="block mt-4">
					<span class="text-gray-800">Email Address</span>
					<input
						class="block w-full mt-2 shadow form-input"
						type="text"
						v-model="account.user.email"
					/>
				</label>
			</div>
		</section>
		<!-- <section class="mt-10">
			<h2 class="text-lg font-medium">Notifications</h2>
			<p class="text-gray-600">
				We send only important changes, but you can choose what you want to hear
				about.
			</p>
			<div class="w-full mt-6 sm:w-1/2">
				<div class="block">
					<div>
						<div class="py-2">
							<label class="inline-flex items-center">
								<input type="checkbox" class="form-checkbox" checked />
								<span class="ml-2">Weekly Usage Summary</span>
							</label>
						</div>
						<div class="py-2">
							<label class="inline-flex items-center">
								<input type="checkbox" class="form-checkbox" />
								<span class="ml-2">Critical Action Required</span>
							</label>
						</div>
						<div class="py-2">
							<label class="inline-flex items-center">
								<input type="checkbox" class="form-checkbox" />
								<span class="ml-2">Site Goes Down</span>
							</label>
						</div>
					</div>
				</div>
			</div>
		</section> -->
		<div class="py-4 mt-10 border-t">
			<ErrorMessage class="mb-4" v-if="errorMessage">
				{{ errorMessage }}
			</ErrorMessage>
			<Button
				type="primary"
				:disabled="state === 'RequestStarted'"
				@click="updateProfile"
			>
				Save changes
			</Button>
		</div>
	</div>
</template>

<script>
import FileUploader from '@/store/fileUploader';

export default {
	name: 'AccountProfile',
	props: ['account'],
	data() {
		return {
			state: null,
			errorMessage: null,
			uploader: null,
			userImage: null,
			uploading: false,
			uploaded: 0,
			total: 0
		};
	},
	methods: {
		onUserImage(e) {
			let file = e.target.files[0];
			this.uploadFile(file);
		},
		async uploadFile(file) {
			this.uploader = new FileUploader();
			this.uploader.on('start', () => {
				this.uploading = true;
			});
			this.uploader.on('progress', data => {
				this.uploaded = data.uploaded;
				this.total = data.total;
			});
			this.uploader.on('error', () => {
				this.uploading = false;
			});
			this.uploader.on('finish', () => {
				this.uploading = false;
			});
			await this.uploader.upload(file, {
				doctype: 'User',
				docname: this.$store.account.user.name,
				method: 'press.api.account.update_profile_picture'
			});
			await this.$store.account.fetchAccount();
			this.notifySuccess();
		},
		async updateProfile() {
			let { first_name, last_name, email } = this.$store.account.user;
			await this.$call('press.api.account.update_profile', {
				first_name,
				last_name,
				email
			});
			this.notifySuccess();
		},
		notifySuccess() {
			this.$notify({
				title: 'Updated profile information',
				icon: 'check',
				color: 'green'
			});
		}
	}
};
</script>
