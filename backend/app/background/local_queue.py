import queue
import threading
import uuid
from typing import Callable, Any
from loguru import logger
from app.background.base_queue import BaseJobQueue

class BackgroundJobManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BackgroundJobManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, num_workers: int = 4):
        if self._initialized:
            return
        self.queue = queue.Queue()
        self.workers = []
        self.num_workers = num_workers
        self._initialized = True
        self._start_workers()

    def _start_workers(self):
        logger.info(f"Starting {self.num_workers} background worker threads...")
        for i in range(self.num_workers):
            t = threading.Thread(target=self._worker_loop, name=f"RAG-Worker-{i}", daemon=True)
            t.start()
            self.workers.append(t)

    def _worker_loop(self):
        while True:
            job_id, job_func, args, kwargs = self.queue.get()
            try:
                logger.info(f"Worker {threading.current_thread().name} starting job {job_id}")
                job_func(*args, **kwargs)
                logger.info(f"Worker {threading.current_thread().name} finished job {job_id}")
            except Exception as e:
                logger.exception(f"Error in background job {job_id}: {e}")
            finally:
                self.queue.task_done()

    def enqueue_job(self, job_func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        job_id = str(uuid.uuid4())
        self.queue.put((job_id, job_func, args, kwargs))
        return job_id

class LocalBackgroundTasksQueue(BaseJobQueue):
    def __init__(self, background_tasks: Any = None):
        self.manager = BackgroundJobManager()

    def enqueue(self, job_func: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
        """
        Pushes a task onto the background execution queue.
        Returns a unique job ID immediately.
        """
        return self.manager.enqueue_job(job_func, *args, **kwargs)
