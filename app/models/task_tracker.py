import os
import json
import time
import threading

class TaskTracker:
    """Track VM creation tasks"""
    
    _instance = None
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls, data_dir='app/data'):
        """Get singleton instance of TaskTracker"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(data_dir)
            return cls._instance
    
    def __init__(self, data_dir='app/data'):
        """Initialize task tracker with data directory"""
        self.data_dir = data_dir
        self.tasks_file = os.path.join(data_dir, 'tasks.json')
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize file if it doesn't exist
        if not os.path.exists(self.tasks_file):
            self._save_tasks({})
        
        # Clean up old tasks on startup
        self._cleanup_old_tasks()
    
    def _load_tasks(self):
        """Load tasks from file"""
        try:
            with open(self.tasks_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_tasks(self, tasks):
        """Save tasks to file"""
        with open(self.tasks_file, 'w') as f:
            json.dump(tasks, f, indent=2)
    
    def add_task(self, task_id, vmid, node, name, task_type='clone'):
        """Add a new VM creation task"""
        tasks = self._load_tasks()
        
        tasks[task_id] = {
            'task_id': task_id,
            'vmid': vmid,
            'node': node,
            'name': name,
            'type': task_type,
            'status': 'running',
            'created_at': time.time(),
            'updated_at': time.time()
        }
        
        self._save_tasks(tasks)
        return tasks[task_id]
    
    def update_task(self, task_id, status):
        """Update task status"""
        tasks = self._load_tasks()
        
        if task_id in tasks:
            tasks[task_id]['status'] = status
            tasks[task_id]['updated_at'] = time.time()
            self._save_tasks(tasks)
            return tasks[task_id]
        
        return None
    
    def get_task(self, task_id):
        """Get a task by ID"""
        tasks = self._load_tasks()
        return tasks.get(task_id)
    
    def get_tasks_for_vm(self, vmid):
        """Get tasks for a specific VM"""
        tasks = self._load_tasks()
        return [task for task in tasks.values() if str(task.get('vmid')) == str(vmid)]
    
    def get_pending_vms(self):
        """Get VMs that are still being created (have active tasks)"""
        tasks = self._load_tasks()
        updated = False
        
        # Check status of all running tasks
        for task_id, task in list(tasks.items()):
            if task.get('status') == 'running':
                # Check if task is still running in Proxmox
                proxmox_status = self.check_task_status(task_id)
                if proxmox_status:
                    # If task is completed, update the status
                    if proxmox_status == 'stopped':
                        task['status'] = 'completed'
                        updated = True
                    # If task failed, update the status
                    elif proxmox_status == 'failed':
                        task['status'] = 'failed'
                        updated = True
                    # Otherwise, task is still running
        
        # Save updated tasks if needed
        if updated:
            self._save_tasks(tasks)
        
        # Only return VMs with running tasks
        pending_vms = {}
        for task in tasks.values():
            if task.get('status') == 'running':
                vmid = task.get('vmid')
                if vmid is not None and vmid not in pending_vms:
                    pending_vms[vmid] = {
                        'vmid': vmid,
                        'name': task.get('name', f'VM {vmid}'),
                        'node': task.get('node', ''),
                        'task_id': task.get('task_id'),
                        'status': 'pending',  # This is the VM status, not task status
                        'type': 'qemu',
                        'mem': 0,
                        'maxmem': 1,
                        'cpu': 0,
                        'maxcpu': 1,
                        'pending_creation': True
                    }
        
        return list(pending_vms.values())
    
    def remove_task(self, task_id):
        """Remove a task"""
        tasks = self._load_tasks()
        
        if task_id in tasks:
            del tasks[task_id]
            self._save_tasks(tasks)
            return True
        
        return False
    
    def _cleanup_old_tasks(self):
        """Remove tasks older than 1 hour"""
        tasks = self._load_tasks()
        current_time = time.time()
        
        # Keep only tasks less than 1 hour old
        updated_tasks = {
            task_id: task for task_id, task in tasks.items()
            if current_time - task.get('created_at', 0) < 3600
        }
        
        if len(updated_tasks) != len(tasks):
            self._save_tasks(updated_tasks)
            
    def check_task_status(self, task_id):
        """Check if a task is still running"""
        from app.proxmox.api import get_api
        
        api = get_api()
        if not api:
            return None
            
        try:
            # Parse the task ID to get node
            if task_id.startswith('UPID:'):
                parts = task_id.split(':')                
                if len(parts) >= 2:
                    node = parts[1]
                    task_endpoint = f"nodes/{node}/tasks/{task_id}/status"
                    status = api.get_request(task_endpoint)
                    
                    if status:
                        return status.get('status')
        except Exception as e:
            print(f"Error checking task status for {task_id}: {str(e)}")
            
        return None
