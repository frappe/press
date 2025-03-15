import ctypes
import os
import platform
from typing import List, Literal


class FWUP:
	def __init__(self):
		self.load_shared_library()

	def warmup(
		self,
		file_paths: List[str],  # noqa: FA100
		method: Literal["psync", "io_uring"] = "psync",
		small_file_size_threshold: int = 1024 * 1024,  # 1MB
		block_size_for_small_files: int = 256 * 1024,  # 256KB
		block_size_for_large_files: int = 256 * 1024,  # 256KB
		small_files_worker_count: int = 1,
		large_files_worker_count: int = 4,
		enable_logging: bool = False,
	) -> None:
		if not file_paths:
			return

		# Create an array of C strings
		file_paths_bytes = [path.encode("utf-8") for path in file_paths]
		c_strings = [ctypes.create_string_buffer(p) for p in file_paths_bytes]
		arr_type = ctypes.c_char_p * len(c_strings)
		c_arr = arr_type(*[ctypes.cast(p, ctypes.c_char_p) for p in c_strings])

		# Get a pointer to the array of C string pointers
		list_ptr = ctypes.cast(ctypes.pointer(c_arr), ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p)))

		# Convert enable_logging to C int
		enable_logging_int = 1 if enable_logging else 0

		# Call the C function with converted arguments
		self.lib.WarmupFiles(
			list_ptr,
			ctypes.c_int(len(file_paths)),
			ctypes.c_char_p(method.encode("utf-8")),
			ctypes.c_long(small_file_size_threshold),
			ctypes.c_long(block_size_for_small_files),
			ctypes.c_long(block_size_for_large_files),
			ctypes.c_int(small_files_worker_count),
			ctypes.c_int(large_files_worker_count),
			ctypes.c_int(enable_logging_int),
		)

	def load_shared_library(self):
		try:
			self.lib = ctypes.cdll.LoadLibrary(self.find_shared_library())
			# Define the WarmupFiles function prototype
			self.lib.WarmupFiles.argtypes = [
				ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p)),  # filePaths
				ctypes.c_int,  # filePathCount
				ctypes.c_char_p,  # method
				ctypes.c_long,  # smallFileSizeThreshold
				ctypes.c_long,  # blockSizeForSmallFiles
				ctypes.c_long,  # blockSizeForLargeFiles
				ctypes.c_int,  # smallFilesWorkerCount
				ctypes.c_int,  # largeFilesWorkerCount
				ctypes.c_int,  # enabledLogging
			]
			self.lib.WarmupFiles.restype = None  # void return type

		except (OSError, RuntimeError) as e:
			raise ImportError(f"Failed to load the WarmupFiles library: {e}")  # noqa: B904

	def find_shared_library(self):
		"""Find and load the appropriate library."""
		machine = platform.machine().lower()
		if machine == "x86_64" or machine == "amd64":
			lib_name = "file_warmer_linux_amd64.so"
		elif machine == "aarch64" or machine == "arm64":
			lib_name = "file_warmer_linux_arm64.so"
		else:
			raise RuntimeError(f"Unsupported Linux architecture: {machine}")

		package_dir = os.path.dirname(os.path.abspath(__file__))
		return os.path.join(package_dir, "lib", lib_name)
