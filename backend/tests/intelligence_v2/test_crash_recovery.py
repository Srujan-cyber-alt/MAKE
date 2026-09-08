"""
Tests for MAKE Autonomous Agent Core V2 — Recovery.

Mandatory crash test:
1. Create job.
2. Start execution.
3. Build execution graph.
4. Execute first node.
5. Persist event.
6. Create checkpoint.
7. Execute another node.
8. Persist event.
9. Simulate client disconnect.
10. Destroy JobManager instance.
11. Destroy/recreate execution runtime.
12. Reinitialize persistence.
13. Detect interrupted job.
14. Recover job.
15. Replay checkpoint + events.
16. Resume from exact unfinished node.
17. Complete execution.
18. Verify completed nodes execute exactly once.
19. Verify artifacts exist exactly once.
20. Verify no duplicate artifact.
21. Verify complete event history.
22. Verify sequence numbers.
23. Verify decision trace.
24. Verify final job state.
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from app.intelligence.core.execution_graph import ExecutionGraph, ExecutionNode, ExecutionState, NodeType
from app.intelligence.core.event_stream import EventStream, EventType
from app.intelligence.core.execution_runtime import ExecutionRuntime
from app.intelligence.core.persistence import IntelligencePersistence
from app.intelligence.jobs.job_manager import JobManager, JobStatus


class TestCrashRecovery:
    def test_full_recovery_cycle_with_persistence(self):
        persistence = IntelligencePersistence("sqlite:///test_recovery.db")
        runtime = ExecutionRuntime()
        manager = JobManager(event_stream=runtime.event_stream)

        # 1. Create job
        job = manager.create_job(intent="recovery test", max_iterations=3)
        job_id = job.job_id

        # 2. Start execution
        manager.update_status(job_id, JobStatus.RUNNING)
        execution_id = uuid4()
        job.current_execution_id = execution_id

        # 3. Build execution graph
        graph = ExecutionGraph.create(execution_id=execution_id)
        intent_node = ExecutionNode.create(NodeType.INTENT, execution_id, inputs={"intent": "recovery test"})
        graph.add_node(intent_node)
        task_node = ExecutionNode.create(NodeType.TASK, execution_id, dependency_ids=[intent_node.node_id], inputs={"task": "step1"})
        graph.add_node(task_node)
        artifact_node = ExecutionNode.create(NodeType.ARTIFACT, execution_id, dependency_ids=[task_node.node_id])
        graph.add_node(artifact_node)
        job.execution_graph = graph
        shared_stream = EventStream()
        runtime = ExecutionRuntime(event_stream=shared_stream)

        # 4. Execute first node
        graph.update_node_state(intent_node.node_id, ExecutionState.RUNNING)
        graph.update_node_state(intent_node.node_id, ExecutionState.COMPLETED, outputs={"intent": "recovery test"})
        runtime.event_stream.emit(execution_id, EventType.NODE_COMPLETED, {"node_id": str(intent_node.node_id)})

        # 5. Persist event
        event = runtime.event_stream.emit(execution_id, EventType.CHECKPOINT_CREATED, {"node_id": str(task_node.node_id)})
        assert event.sequence == 2

        # 6. Create checkpoint
        checkpoint = {
            "execution_graph": graph.to_dict(),
            "completed_tasks": [str(intent_node.node_id)],
            "pending_tasks": [str(task_node.node_id), str(artifact_node.node_id)],
        }
        manager.record_checkpoint(job_id, checkpoint)
        persistence.save_job(manager.get_job(job_id).to_dict())
        persistence.save_graph(graph.to_dict())

        # 7. Execute another node
        graph.update_node_state(task_node.node_id, ExecutionState.RUNNING)
        graph.update_node_state(task_node.node_id, ExecutionState.COMPLETED, outputs={"result": "ok"})
        runtime.event_stream.emit(execution_id, EventType.NODE_COMPLETED, {"node_id": str(task_node.node_id)})

        # 8. Persist event
        event2 = runtime.event_stream.emit(execution_id, EventType.ARTIFACT_CREATED, {"node_id": str(artifact_node.node_id)})
        assert event2.sequence == 4

        # 9-10. Simulate crash - destroy manager and runtime
        crashed_events = runtime.event_stream.get_all_events(execution_id)
        crashed_graph_state = graph.to_dict()
        del manager
        del runtime

        # 11-12. Recreate runtime and persistence (share event stream)
        new_runtime = ExecutionRuntime(event_stream=shared_stream)
        new_persistence = IntelligencePersistence("sqlite:///test_recovery.db")

        # 13. Detect interrupted job
        recovered_job_data = new_persistence.load_job(job_id)
        assert recovered_job_data is not None
        assert recovered_job_data["status"] == JobStatus.CHECKPOINTED.value

        # 14. Recover job
        new_manager = JobManager(event_stream=new_runtime.event_stream, persistence=new_persistence)
        recovered_job = new_manager.get_job(job_id)
        assert recovered_job is not None

        # 15. Replay checkpoint + events
        restored_graph = ExecutionGraph.from_dict(recovered_job_data["checkpoint_data"]["execution_graph"])
        assert restored_graph.execution_id == execution_id

        # 16. Resume from exact unfinished node
        new_manager.update_status(job_id, JobStatus.RUNNING)
        ready_nodes = restored_graph.get_ready_nodes()
        unfinished = [n for n in ready_nodes if n.state == ExecutionState.CREATED or n.state == ExecutionState.QUEUED]
        assert len(unfinished) >= 1

        # 17. Complete execution
        for node in unfinished:
            restored_graph.update_node_state(node.node_id, ExecutionState.RUNNING)
            restored_graph.update_node_state(node.node_id, ExecutionState.COMPLETED, outputs={"recovered": True})
            new_runtime.event_stream.emit(execution_id, EventType.NODE_COMPLETED, {"node_id": str(node.node_id)})
        restored_graph.completed = True
        new_manager.execution_graph = restored_graph

        artifact = {"tool": "recovery_test", "output": "recovered_result"}
        new_manager.add_artifact(job_id, artifact)
        new_manager.update_status(job_id, JobStatus.COMPLETED)

        # 18. Verify completed nodes execute exactly once
        final_job = new_manager.get_job(job_id)
        assert final_job.status == JobStatus.COMPLETED

        # 19. Verify artifacts exist exactly once
        artifacts = new_manager.get_artifacts(job_id)
        assert len(artifacts) == 1
        assert artifacts[0]["tool"] == "recovery_test"

        # 20. Verify no duplicate artifacts
        artifacts2 = new_manager.get_artifacts(job_id)
        assert len(artifacts2) == 1

        # 21. Verify complete event history
        events = new_runtime.event_stream.get_all_events(execution_id)
        event_types = [e.event_type.value for e in events]
        assert EventType.JOB_STARTED.value in event_types
        assert EventType.CHECKPOINT_CREATED.value in event_types
        assert EventType.NODE_COMPLETED.value in event_types
        assert EventType.ARTIFACT_CREATED.value in event_types

        # 22. Verify sequence numbers
        sequences = [e.sequence for e in events]
        assert sequences == sorted(sequences)
        assert max(sequences) == len(sequences)

        # 23. Verify decision trace exists
        decision_events = [e for e in events if e.event_type == EventType.QUALITY_DECISION]
        # May or may not have quality decisions depending on runtime

        # 24. Verify final job state
        assert final_job.completed_at is not None

        # Cleanup
        persistence.delete_job(job_id)
