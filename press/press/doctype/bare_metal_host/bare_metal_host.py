import frappe
from frappe.model.document import Document
from press.agent import Agent

class BareMetalHost(Document):
    def validate(self):
        self.validate_resources()
        if not self.available_cpu:
            self.available_cpu = self.total_cpu
        if not self.available_memory:
            self.available_memory = self.total_memory
        if not self.available_disk:
            self.available_disk = self.total_disk

    def validate_resources(self):
        if self.available_cpu > self.total_cpu:
            frappe.throw("Available CPU cannot be more than total CPU")
        if self.available_memory > self.total_memory:
            frappe.throw("Available memory cannot be more than total memory")
        if self.available_disk > self.total_disk:
            frappe.throw("Available disk cannot be more than total disk")

    def allocate_resources(self, cpu, memory, disk):
        """Allocate resources for a new VM"""
        if cpu > self.available_cpu:
            frappe.throw(f"Not enough CPU available. Required: {cpu}, Available: {self.available_cpu}")
        if memory > self.available_memory:
            frappe.throw(f"Not enough memory available. Required: {memory}, Available: {self.available_memory}")
        if disk > self.available_disk:
            frappe.throw(f"Not enough disk space available. Required: {disk}, Available: {self.available_disk}")

        self.available_cpu -= cpu
        self.available_memory -= memory
        self.available_disk -= disk
        self.save()

    def deallocate_resources(self, cpu, memory, disk):
        """Release resources when a VM is deleted"""
        self.available_cpu = min(self.total_cpu, self.available_cpu + cpu)
        self.available_memory = min(self.total_memory, self.available_memory + memory)
        self.available_disk = min(self.total_disk, self.available_disk + disk)
        self.save()

    def get_agent(self):
        """Get agent instance for this host"""
        return Agent(self.name, server_type="Bare Metal Host") 