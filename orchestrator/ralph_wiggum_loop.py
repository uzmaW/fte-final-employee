"""
ralph_wiggum_loop.py - Task persistence and multi-step completion (Ralph Wiggum Stop Hook).

Backs the .claude/skills/ralph-wiggum-loop/SKILL.md specification.
Implements the stop hook pattern that keeps Claude iterating until a task is complete.
"""

import json
import time
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import get_settings
from utilities.vault_manager import VaultManager
from utilities.retry_handler import with_retry, TransientError

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CHECKPOINT = "checkpoint"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskState:
    task_id: str
    status: str = TaskStatus.PENDING.value
    objective: str = ""
    total_steps: int = 0
    current_step: int = 0
    completed_steps: List[int] = field(default_factory=list)
    failed_steps: List[int] = field(default_factory=list)
    max_iterations: int = 10
    current_iteration: int = 0
    created_at: str = ""
    started_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    result: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskState':
        """Create TaskState from dict, filtering unknown keys."""
        clean = {
            'task_id': data.get('task_id', ''),
            'status': data.get('status', TaskStatus.PENDING.value),
            'objective': data.get('objective', ''),
            'total_steps': int(data.get('total_steps', 0)),
            'current_step': int(data.get('current_step', 0)),
            'completed_steps': data.get('completed_steps', []),
            'failed_steps': data.get('failed_steps', []),
            'max_iterations': int(data.get('max_iterations', 10)),
            'current_iteration': int(data.get('current_iteration', 0)),
            'created_at': data.get('created_at', ''),
            'started_at': data.get('started_at', ''),
            'updated_at': data.get('updated_at', ''),
            'completed_at': data.get('completed_at', ''),
            'result': data.get('result', ''),
            'error': data.get('error', ''),
            'metadata': data.get('metadata', {}) if isinstance(data.get('metadata'), dict) else {},
        }
        return cls(**clean)


class RalphWiggumLoop:
    """
    Ralph Wiggum loop for autonomous multi-step task completion.

    The loop pattern:
    1. Read task state file
    2. Extract current step
    3. Execute step
    4. Update state
    5. Check completion → move to Done/ if complete
    6. If not complete → re-inject prompt and repeat

    Two completion strategies:
    A) File movement: complete when file moves to /Done/
    B) Marker-based: status field = complete
    """

    def __init__(self, vault_path: str, max_iterations: int = 10,
                 iteration_delay: float = 1.0, timeout_hours: float = 48.0):
        self.vault_path = Path(vault_path)
        self.max_iterations = max_iterations
        self.iteration_delay = iteration_delay
        self.timeout_hours = timeout_hours
        self.settings = get_settings()
        self.vault_manager = VaultManager()

        self.tasks_dir = self.vault_path / 'Tasks'
        self.in_progress_dir = self.vault_path / 'In_Progress'
        self.done_dir = self.vault_path / 'Done'
        self.logs_dir = self.vault_path / 'Logs'

        self.stats = {
            'tasks_completed': 0, 'tasks_failed': 0,
            'tasks_timeout': 0, 'max_iterations_hit': 0,
            'iterations_total': 0, 'started_at': datetime.now().isoformat()
        }
        self._running = False
        self._current_task_id = None

    def create_task(self, task_id: str, objective: str,
                    steps: List[str], metadata: Dict = None) -> Path:
        """Create a new multi-step task."""
        now = datetime.now().isoformat()
        yaml_lines = [
            '---',
            f'type: multi_step_task',
            f'task_id: {task_id}',
            'status: pending',
            f'objective: "{objective}"',
            f'total_steps: {len(steps)}',
            'current_step: 0',
            f'max_iterations: {self.max_iterations}',
            f'created_at: "{now}"',
            f'metadata: {json.dumps(metadata or {})}',
            '---', '',
            f'# Task: {objective}', '', '## Steps', ''
        ]
        for i, step in enumerate(steps, 1):
            yaml_lines.append(f'{i}. [ ] {step}')
        yaml_lines.extend(['', '## Progress Log', ''])

        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        task_file = self.tasks_dir / f'TASK_{task_id}.md'
        task_file.write_text('\n'.join(yaml_lines))
        logger.info(f"Created task: {task_id} with {len(steps)} steps")
        return task_file

    def load_task(self, task_file: Path) -> Optional[TaskState]:
        """Load task state from file."""
        try:
            content = task_file.read_text()
            parts = content.split('---')
            if len(parts) >= 3:
                metadata = {}
                for line in parts[1].strip().split('\n'):
                    if ':' in line:
                        k, v = line.split(':', 1)
                        k = k.strip()
                        v = v.strip().strip('"')
                        if k in ('total_steps', 'current_step', 'max_iterations', 'current_iteration'):
                            metadata[k] = int(v) if v.isdigit() else 0
                        elif k == 'metadata':
                            try:
                                metadata[k] = json.loads(v)
                            except (json.JSONDecodeError, ValueError):
                                metadata[k] = {}
                        else:
                            metadata[k] = v
                return TaskState.from_dict(metadata)
        except Exception as e:
            logger.error(f"Error loading task {task_file}: {e}")
        return None

    def save_task(self, task: TaskState) -> None:
        """Save task state to file."""
        task_file = self.tasks_dir / f'TASK_{task.task_id}.md'
        if task_file.exists():
            content = task_file.read_text()
            yaml_start = content.find('---')
            yaml_end = content.find('---', yaml_start + 3)
            if yaml_start >= 0 and yaml_end > yaml_start:
                yaml_data = (
                    f'---\ntype: multi_step_task\ntask_id: {task.task_id}\n'
                    f'status: {task.status}\nobjective: "{task.objective}"\n'
                    f'total_steps: {task.total_steps}\ncurrent_step: {task.current_step}\n'
                    f'max_iterations: {task.max_iterations}\n'
                    f'current_iteration: {task.current_iteration}\n'
                    f'created_at: "{task.created_at}"\n'
                    f'started_at: "{task.started_at}"\n'
                    f'updated_at: "{task.updated_at}"\n'
                    f'completed_at: "{task.completed_at}"\n'
                    f'result: {task.result}\nerror: "{task.error}"\n---\n'
                )
                body = content[yaml_end + 3:]
                task_file.write_text(yaml_data + body)

    def check_completion(self, task: TaskState) -> bool:
        """Check if task is complete using all three strategies."""
        # Strategy A: File in Done/
        if (self.done_dir / f'TASK_{task.task_id}.md').exists():
            return True
        # Strategy B: Status marker
        if task.status == TaskStatus.COMPLETE.value:
            return True
        # Strategy C: All steps checked
        if task.total_steps > 0:
            tf = self.tasks_dir / f'TASK_{task.task_id}.md'
            if tf.exists():
                checked = tf.read_text().count('[x]') + tf.read_text().count('[X]')
                if checked >= task.total_steps:
                    return True
        return False

    def move_to_done(self, task: TaskState, result: str = 'success') -> Path:
        """Move completed task to Done/."""
        task.completed_at = datetime.now().isoformat()
        task.result = result
        task.status = TaskStatus.COMPLETE.value
        self.save_task(task)

        src = self.tasks_dir / f'TASK_{task.task_id}.md'
        dst = self.done_dir / f'TASK_{task.task_id}.md'
        if src.exists():
            src.rename(dst)

        for agent_dir in self.in_progress_dir.glob('*'):
            ipf = agent_dir / f'TASK_{task.task_id}.md'
            if ipf.exists():
                ipf.unlink()

        self.stats['tasks_completed'] += 1
        self.vault_manager.log_event(
            event_type='task_completed', task_id=task.task_id,
            details={'result': result, 'iterations': task.current_iteration}
        )
        logger.info(f"Task completed: {task.task_id}")
        return dst

    def move_to_failed(self, task: TaskState, error: str) -> Path:
        """Move failed task to error state."""
        task.error = error
        task.status = TaskStatus.FAILED.value
        task.completed_at = datetime.now().isoformat()
        self.save_task(task)

        src = self.tasks_dir / f'TASK_{task.task_id}.md'
        failed_dir = self.logs_dir / 'FAILED'
        failed_dir.mkdir(parents=True, exist_ok=True)
        dst = failed_dir / f'TASK_{task.task_id}.md'
        if src.exists():
            src.rename(dst)

        self.stats['tasks_failed'] += 1
        self.vault_manager.log_event(
            event_type='task_failed', task_id=task.task_id,
            details={'error': error}
        )
        logger.error(f"Task failed: {task.task_id} - {error}")
        return dst

    def run_step(self, task: TaskState, step_fn: Callable) -> bool:
        """
        Run one iteration of the task loop.

        Args:
            task: Current task state
            step_fn: Callable that executes one step, returns True if step done

        Returns:
            True if task is complete
        """
        if task.current_iteration >= self.max_iterations:
            self.move_to_failed(task, f'Max iterations ({self.max_iterations}) exceeded')
            self.stats['max_iterations_hit'] += 1
            return True

        if not task.started_at:
            task.started_at = datetime.now().isoformat()

        task.current_iteration += 1
        task.current_step += 1
        task.updated_at = datetime.now().isoformat()
        self.stats['iterations_total'] += 1

        try:
            step_done = step_fn(task)
            if step_done:
                task.completed_steps.append(task.current_step)

            if self.check_completion(task):
                self.move_to_done(task)
                return True

            self.save_task(task)
            return False

        except TransientError as e:
            logger.warning(f"Transient error in task {task.task_id}: {e}")
            task.error = str(e)
            self.save_task(task)
            time.sleep(self.iteration_delay)
            return False

        except Exception as e:
            logger.error(f"Error in task {task.task_id}: {e}")
            self.move_to_failed(task, str(e))
            return True

    def run(self, task_id: str, step_fn: Callable, objective: str = None,
            steps: List[str] = None) -> bool:
        """
        Run the Ralph Wiggum loop for a task until completion.

        Args:
            task_id: Task identifier
            step_fn: Callable that executes one step
            objective: Task objective (used if creating new task)
            steps: Step descriptions (used if creating new task)

        Returns:
            True if task completed successfully
        """
        self._running = True
        self._current_task_id = task_id

        task_file = self.tasks_dir / f'TASK_{task_id}.md'
        if task_file.exists():
            task = self.load_task(task_file)
        elif objective and steps:
            self.create_task(task_id, objective, steps)
            task = self.load_task(task_file)
        else:
            logger.error(f"Task {task_id} not found and no creation params provided")
            return False

        iteration = 0
        timeout_at = datetime.now() + timedelta(hours=self.timeout_hours)

        while self._running:
            if datetime.now() > timeout_at:
                self.move_to_failed(task, f'Task timed out after {self.timeout_hours}h')
                self.stats['tasks_timeout'] += 1
                return False

            complete = self.run_step(task, step_fn)
            if complete:
                return task.status == TaskStatus.COMPLETE.value

            iteration += 1
            time.sleep(self.iteration_delay)

        return False

    def stop(self):
        """Stop the loop gracefully."""
        self._running = False
        logger.info(f"Ralph Wiggum loop stopped. Stats: {self.stats}")

    def get_stats(self) -> Dict[str, Any]:
        """Return loop statistics."""
        return {
            **self.stats,
            'uptime_seconds': (datetime.now() - datetime.fromisoformat(
                self.stats['started_at'])).total_seconds()
        }


# ─── Standalone Execution ────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Wiggum Loop')
    parser.add_argument('--vault-path', default='AI_Employee_Vault', help='Vault path')
    parser.add_argument('--max-iterations', type=int, default=5, help='Max iterations')
    parser.add_argument('--demo', action='store_true', help='Run demo with sample task')
    parser.add_argument('--test', action='store_true', help='Run self-test')

    args = parser.parse_args()

    loop = RalphWiggumLoop(
        vault_path=args.vault_path,
        max_iterations=args.max_iterations
    )

    if args.demo:
        print("=" * 60)
        print("Ralph Wiggum Loop Demo")
        print("=" * 60)

        task_id = f"DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        steps = ['Step 1: Gather data', 'Step 2: Analyze', 'Step 3: Report']

        def demo_step_fn(task):
            print(f"  Iteration {task.current_iteration}: Executing step {task.current_step}...")
            return task.current_step >= task.total_steps

        completed = loop.run(task_id, demo_step_fn,
                            objective='Demo task', steps=steps)
        print(f"\nTask {'completed' if completed else 'failed'}!")

    if args.test:
        print("=" * 60)
        print("Ralph Wiggum Loop Self-Test")
        print("=" * 60)

        # Test 1: Create task
        tid = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_file = loop.create_task(tid, 'Test objective', ['Step A', 'Step B'])
        assert task_file.exists(), "Task file should exist"
        print(f"✓ Task created: {task_file.name}")

        # Test 2: Load task
        loaded = loop.load_task(task_file)
        assert loaded is not None, "Should load task"
        assert loaded.task_id == tid
        assert loaded.total_steps == 2
        assert loaded.status == 'pending'
        print(f"✓ Task loaded: {loaded.task_id}, {loaded.total_steps} steps")

        # Test 3: Check completion (not complete)
        assert not loop.check_completion(loaded), "Should not be complete yet"
        print("✓ Incomplete task detected correctly")

        # Test 4: Move to done manually
        loaded.status = 'complete'
        done_path = loop.move_to_done(loaded)
        assert done_path.exists(), "Done file should exist"
        print(f"✓ Task moved to Done: {done_path.name}")

        # Test 5: Check completion (now complete)
        assert loop.check_completion(loaded), "Should be complete"
        print("✓ Completed task detected correctly")

        # Test 6: Stats
        stats = loop.get_stats()
        assert 'tasks_completed' in stats
        print(f"✓ Stats: tasks_completed={stats['tasks_completed']}")

        print("\n✓ All Ralph Wiggum Loop tests passed!")