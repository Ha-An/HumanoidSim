from __future__ import annotations

import json
from typing import Any

import rclpy
from rclpy.action import ActionServer
from rclpy.node import Node
from std_msgs.msg import String

from humanoidsim import (
    StateTransitionEvent,
    build_incident_transition_event,
    default_humanoid_state,
    expand_task_steps,
    get_incident_profile,
    load_incident_schema,
    load_state_schema,
    transition_humanoid_state,
    validate_state_transition,
)
from humanoidsim_ros_interfaces.action import ExecutePrimitive, ExecuteTask, RecoverIncident
from humanoidsim_ros_interfaces.srv import ExpandTask, GetIncidentProtocol, InjectIncident, ValidateTransition


class HumanoidSimBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__("humanoidsim_bridge_node")
        self.state_schema = load_state_schema()
        self.incident_schema = load_incident_schema()
        self.states: dict[str, Any] = {}
        self.event_pub = self.create_publisher(String, "/humanoidsim/events", 10)
        self.state_publishers: dict[str, Any] = {}

        self.create_service(ExpandTask, "/humanoidsim/expand_task", self._expand_task)
        self.create_service(ValidateTransition, "/humanoidsim/validate_transition", self._validate_transition)
        self.create_service(InjectIncident, "/humanoidsim/inject_incident", self._inject_incident)
        self.create_service(GetIncidentProtocol, "/humanoidsim/get_incident_protocol", self._get_incident_protocol)
        self.execute_task_server = ActionServer(self, ExecuteTask, "/humanoidsim/execute_task", self._execute_task)
        self.execute_primitive_server = ActionServer(self, ExecutePrimitive, "/humanoidsim/execute_primitive", self._execute_primitive)
        self.recover_incident_server = ActionServer(self, RecoverIncident, "/humanoidsim/recover_incident", self._recover_incident)

    def _state_for(self, humanoid_id: str):
        if humanoid_id not in self.states:
            self.states[humanoid_id] = default_humanoid_state(humanoid_id)
        return self.states[humanoid_id]

    def _publish_state(self, humanoid_id: str, state: Any) -> None:
        self.states[humanoid_id] = state
        topic = f"/humanoid/{humanoid_id}/state"
        if humanoid_id not in self.state_publishers:
            self.state_publishers[humanoid_id] = self.create_publisher(String, topic, 10)
        msg = String()
        msg.data = json.dumps(state.to_dict(), ensure_ascii=False)
        self.state_publishers[humanoid_id].publish(msg)

    def _publish_event(self, payload: dict[str, Any]) -> None:
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False)
        self.event_pub.publish(msg)

    def _expand_task(self, request, response):
        try:
            args = _loads(request.args_json)
            response.steps_json = json.dumps(expand_task_steps(request.task_code, args), ensure_ascii=False)
            response.success = True
            response.message = "ok"
        except Exception as exc:  # noqa: BLE001 - ROS service reports errors in response.
            response.success = False
            response.steps_json = "[]"
            response.message = str(exc)
        return response

    def _validate_transition(self, request, response):
        try:
            previous = _loads(request.previous_state_json)
            event = _loads(request.event_json)
            next_state = transition_humanoid_state(previous, event, schema=self.state_schema, strict=False)
            issues = validate_state_transition(previous, next_state, event, schema=self.state_schema, strict=False)
            response.valid = not issues
            response.next_state_json = json.dumps(next_state.to_dict(), ensure_ascii=False)
            response.issues_json = json.dumps([issue.__dict__ for issue in issues], ensure_ascii=False)
            response.message = "ok"
        except Exception as exc:  # noqa: BLE001
            response.valid = False
            response.next_state_json = "{}"
            response.issues_json = "[]"
            response.message = str(exc)
        return response

    def _inject_incident(self, request, response):
        try:
            context = _loads(request.context_json)
            state = self._state_for(request.humanoid_id)
            event = build_incident_transition_event(
                request.incident_code,
                task_code=context.get("task_code"),
                task_instance_id=context.get("task_instance_id"),
                primitive_call_code=context.get("primitive_call_code"),
                schema=self.incident_schema,
            )
            next_state = transition_humanoid_state(state, event, schema=self.state_schema)
            self._publish_state(request.humanoid_id, next_state)
            profile = get_incident_profile(request.incident_code, schema=self.incident_schema)
            response.accepted = True
            response.state_json = json.dumps(next_state.to_dict(), ensure_ascii=False)
            response.recovery_protocol_json = json.dumps([step.to_dict() for step in profile.recovery_protocol], ensure_ascii=False)
            response.message = "ok"
            self._publish_event({"type": "incident", "humanoid_id": request.humanoid_id, "incident_code": profile.code})
        except Exception as exc:  # noqa: BLE001
            response.accepted = False
            response.state_json = "{}"
            response.recovery_protocol_json = "[]"
            response.message = str(exc)
        return response

    def _get_incident_protocol(self, request, response):
        try:
            profile = get_incident_profile(request.incident_code, schema=self.incident_schema)
            response.success = True
            response.profile_json = json.dumps(profile.to_dict(), ensure_ascii=False)
            response.message = "ok"
        except Exception as exc:  # noqa: BLE001
            response.success = False
            response.profile_json = "{}"
            response.message = str(exc)
        return response

    def _execute_task(self, goal_handle):
        goal = goal_handle.request
        humanoid_id = goal.humanoid_id or "H1"
        state = self._state_for(humanoid_id)
        feedback = ExecuteTask.Feedback()
        try:
            state = transition_humanoid_state(
                state,
                StateTransitionEvent(event_type="task_assigned", task_code=goal.task_code, task_instance_id=goal.task_instance_id),
                schema=self.state_schema,
            )
            state = transition_humanoid_state(
                state,
                StateTransitionEvent(event_type="task_started", task_code=goal.task_code, task_instance_id=goal.task_instance_id),
                schema=self.state_schema,
            )
            self._publish_state(humanoid_id, state)
            steps = expand_task_steps(goal.task_code, _loads(goal.args_json))
            primitive_steps = [step for step in steps if step.get("call_level") == "PRIMITIVE_SKILL"]
            for index, step in enumerate(primitive_steps):
                owner_task = str(step.get("parent_task_code") or goal.task_code)
                state = transition_humanoid_state(
                    state,
                    StateTransitionEvent(
                        event_type="primitive_started",
                        task_code=owner_task,
                        task_instance_id=goal.task_instance_id,
                        step_id=str(step.get("step_id", "")),
                        primitive_call_code=str(step.get("call_code", "")),
                    ),
                    schema=self.state_schema,
                )
                self._publish_state(humanoid_id, state)
                feedback.current_step_code = str(step.get("call_code", ""))
                feedback.state_json = json.dumps(state.to_dict(), ensure_ascii=False)
                feedback.progress = float((index + 1) / max(1, len(primitive_steps)))
                goal_handle.publish_feedback(feedback)
                state = transition_humanoid_state(
                    state,
                    StateTransitionEvent(
                        event_type="primitive_finished",
                        task_code=owner_task,
                        task_instance_id=goal.task_instance_id,
                        step_id=str(step.get("step_id", "")),
                        primitive_call_code=str(step.get("call_code", "")),
                    ),
                    schema=self.state_schema,
                )
            state = transition_humanoid_state(
                state,
                StateTransitionEvent(event_type="task_completed", task_code=goal.task_code, task_instance_id=goal.task_instance_id),
                schema=self.state_schema,
            )
            self._publish_state(humanoid_id, state)
            goal_handle.succeed()
            result = ExecuteTask.Result()
            result.success = True
            result.final_state_json = json.dumps(state.to_dict(), ensure_ascii=False)
            result.message = "ok"
            return result
        except Exception as exc:  # noqa: BLE001
            goal_handle.abort()
            result = ExecuteTask.Result()
            result.success = False
            result.final_state_json = json.dumps(state.to_dict(), ensure_ascii=False)
            result.message = str(exc)
            return result

    def _execute_primitive(self, goal_handle):
        goal = goal_handle.request
        humanoid_id = goal.humanoid_id or "H1"
        state = self._state_for(humanoid_id)
        try:
            for event_type, progress in (("primitive_started", 0.5), ("primitive_finished", 1.0)):
                state = transition_humanoid_state(
                    state,
                    StateTransitionEvent(
                        event_type=event_type,
                        task_code=goal.task_code,
                        task_instance_id=goal.task_instance_id,
                        step_id=goal.step_id,
                        primitive_call_code=goal.primitive_call_code,
                    ),
                    schema=self.state_schema,
                )
                feedback = ExecutePrimitive.Feedback()
                feedback.state_json = json.dumps(state.to_dict(), ensure_ascii=False)
                feedback.progress = progress
                goal_handle.publish_feedback(feedback)
            self._publish_state(humanoid_id, state)
            goal_handle.succeed()
            result = ExecutePrimitive.Result()
            result.success = True
            result.final_state_json = json.dumps(state.to_dict(), ensure_ascii=False)
            result.message = "ok"
            return result
        except Exception as exc:  # noqa: BLE001
            goal_handle.abort()
            result = ExecutePrimitive.Result()
            result.success = False
            result.final_state_json = json.dumps(state.to_dict(), ensure_ascii=False)
            result.message = str(exc)
            return result

    def _recover_incident(self, goal_handle):
        goal = goal_handle.request
        humanoid_id = goal.humanoid_id or "H1"
        state = self._state_for(humanoid_id)
        try:
            incident_event = build_incident_transition_event(
                goal.incident_code,
                task_code=goal.task_code,
                task_instance_id=goal.task_instance_id,
                schema=self.incident_schema,
            )
            state = transition_humanoid_state(state, incident_event, schema=self.state_schema)
            profile = get_incident_profile(goal.incident_code, schema=self.incident_schema)
            steps = profile.recovery_protocol
            for index, step in enumerate(steps):
                feedback = RecoverIncident.Feedback()
                feedback.current_recovery_step_code = step.code
                feedback.state_json = json.dumps(state.to_dict(), ensure_ascii=False)
                feedback.progress = float((index + 1) / max(1, len(steps)))
                goal_handle.publish_feedback(feedback)
            self._publish_state(humanoid_id, state)
            goal_handle.succeed()
            result = RecoverIncident.Result()
            result.success = True
            result.final_state_json = json.dumps(state.to_dict(), ensure_ascii=False)
            result.message = "ok"
            return result
        except Exception as exc:  # noqa: BLE001
            goal_handle.abort()
            result = RecoverIncident.Result()
            result.success = False
            result.final_state_json = json.dumps(state.to_dict(), ensure_ascii=False)
            result.message = str(exc)
            return result


def _loads(raw: str) -> dict[str, Any]:
    raw = str(raw or "").strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    return payload if isinstance(payload, dict) else {}


def main() -> None:
    rclpy.init()
    node = HumanoidSimBridgeNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
