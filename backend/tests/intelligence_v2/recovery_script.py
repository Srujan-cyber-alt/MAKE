#!/usr/bin/env python3
"""
Standalone recovery script for process crash test.
Run as subprocess, then kill, then run recovery.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, NodeType, ExecutionState
from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.persistence import IntelligencePersistence
from app.intelligence.jobs.job_manager import JobManager, JobStatus


def create_and_checkpoint(db_path: str):
    persistence = IntelligencePersistence(f"sqlite:///{os.path.abspath(db_path)}")
    manager = JobManager(persistence=persistence)
    job = manager.create_job(intent="crash recovery test", max_iterations=3)
    job_id = job.job_id
    execution_id = uuid4()
    graph = ExecutionGraph.create(execution_id=execution_id)
    intent_node = ExecutionNode.create(NodeType.INTENT, execution_id, inputs={"intent": "crash recovery test"})
    graph.add_node(intent_node)
    task_node = ExecutionNode.create(NodeType.TASK, execution_id, dependency_ids=[intent_node.node_id])
    graph.add_node(task_node)
    graph.update_node_state(intent_node.node_id, ExecutionState.COMPLETED)
    manager.record_checkpoint(job_id, {"execution_graph": graph.to_dict(), "execution_id": str(execution_id)})
    manager.update_status(job_id, JobStatus.CHECKPOINTED)
    manager.add_artifact(job_id, {"tool": "pre_crash", "output": "artifact_before_crash"})
    return str(job_id), str(execution_id)


def recover(db_path: str, job_id: str, execution_id: str):
    persistence = IntelligencePersistence(f"sqlite:///{os.path.abspath(db_path)}")
    manager = JobManager(persistence=persistence)
    job = manager.get_job(UUID(job_id))
    assert job is not None, "Job not found after recovery"
    assert job.status == JobStatus.CHECKPOINTED, f"Job status is {job.status}, expected CHECKPOINTED"
    graph = manager.resume_from_checkpoint(UUID(job_id))
    assert graph is not None, "Graph not restored from checkpoint"
    assert graph.execution_id == UUID(execution_id), "Execution ID mismatch"
    ready = graph.get_ready_nodes()
    assert len(ready) >= 1, "No ready nodes after recovery"
    for node in ready:
        graph.update_node_state(node.node_id, ExecutionState.COMPLETED, outputs={"recovered": True})
    graph.completed = True
    manager.add_artifact(UUID(job_id), {"tool": "post_recovery", "output": "artifact_after_recovery"})
    manager.update_status(UUID(job_id), JobStatus.COMPLETED)
    artifacts = manager.get_artifacts(UUID(job_id))
    assert len(artifacts) == 2, f"Expected 2 artifacts, got {len(artifacts)}"
    return True


if __name__ == "__main__":
    mode = sys.argv[1]
    db_path = sys.argv[2]
    if mode == "create":
        job_id, execution_id = create_and_checkpoint(db_path)
        print(f"CREATED {job_id} {execution_id}")
    elif mode == "recover":
        job_id = sys.argv[3]
        execution_id = sys.argv[4]
        recover(db_path, job_id, execution_id)
        print("RECOVERED")
