# Primitive Reference

## Generic Request Resolution

`PRIMITIVE_IDENTIFY_ITEM`은 이미 정해진 item id를 확인하는 데에도 쓰이고, generic item request를 concrete item instance로 확정하는 데에도 쓰입니다. 예를 들어 `REPLENISH_MATERIAL`이 `entity_type=material`, `selection_policy=available_material_from_source`를 입력으로 받으면, 이 primitive 단계에서 실제로 집을 수 있는 material slot과 `MAT-WH-*` item id를 선택합니다.

이 primitive는 task 의미를 바꾸지 않습니다. Task는 “material 보충”이라는 목표를 유지하고, primitive는 그 목표를 실행 가능한 concrete 대상에 연결합니다.

이 문서는 task step에서 실제로 참조되는 active primitive skill과 primitive registry를 정리한 reference입니다. Primitive는 task를 구성하는 가장 작은 실행 skill이며, `ATOMIC_TASK`와 `COMPOSITE_TASK`의 step에서 참조됩니다.

## 요약

- Active primitive 수: 59
- Registry primitive 수: 59
- 원본 primitive 정의: `data/primitives/*.json`
- Primitive template index: `data/primitive_templates.json`
- State relation 원본: 각 primitive JSON의 `metadata.state`, `data/state_schema_core.json`의 `primitive_state_profiles`
- 정상적으로 실행 중인 모든 primitive는 Availability State 중 `EXECUTING`으로 표현됩니다.
- Incident recovery protocol 안에서 실행되는 primitive는 예외적으로 `BLOCKED` 상태를 유지합니다. 이때 primitive code는 `task_context.primitive_call_code`에 기록되며, UI에서는 `CODE (RECOVERY)`처럼 표시할 수 있습니다.

## Active Primitive와 Registry Primitive

<table>
  <colgroup>
    <col style="width: 16%;" />
    <col style="width: 44%;" />
    <col style="width: 20%;" />
    <col style="width: 20%;" />
  </colgroup>
  <thead>
    <tr>
      <th>용어</th>
      <th>의미</th>
      <th>기준 파일/필드</th>
      <th>사용 목적</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Active primitive</td>
      <td>현재 task catalog의 `steps`에서 `expected_level=PRIMITIVE_SKILL`로 직접 참조되는 primitive입니다. 실제 task sequence를 이루는 실행 leaf step입니다.</td>
      <td>`data/tasks/*.json`의 `steps[].call_code`</td>
      <td>task reference, 실행 coverage, ManSim primitive 지원 범위 확인</td>
    </tr>
    <tr>
      <td>Registry primitive</td>
      <td>HumanoidSim primitive registry에 등록된 전체 primitive 정의입니다. 현재 task가 쓰지 않더라도, 추후 task나 recovery protocol에서 재사용할 수 있습니다.</td>
      <td>`data/primitives/*.json`, `data/task_catalog_core.json`의 primitive entry</td>
      <td>schema validation, hierarchy validation, custom task 확장</td>
    </tr>
  </tbody>
</table>

개념적으로는 `active primitive <= registry primitive`입니다. 현재 v0.1 catalog에서는 둘의 수가 같을 수 있지만, custom task를 만들거나 future primitive를 먼저 등록하면 registry에만 존재하는 primitive가 생길 수 있습니다.

## Primitive와 State 관계

Primitive는 Humanoid가 지금 어떤 실행 단계를 수행하는지를 나타냅니다. State는 그 실행 동안 Humanoid가 어떤 운용 상태인지를 나타냅니다. 따라서 primitive 자체가 state는 아니지만, primitive 시작/종료 event가 HumanoidSim state transition을 유도합니다.

<table>
  <colgroup>
    <col style="width: 35%;" />
    <col style="width: 65%;" />
  </colgroup>
  <thead>
    <tr>
      <th>필드</th>
      <th>의미</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>metadata.state.availability.running</code></td>
      <td>primitive 실행 중의 Availability State입니다. 모든 primitive는 `EXECUTING`을 사용합니다.</td>
    </tr>
    <tr>
      <td><code>metadata.state.allowed.mobility</code></td>
      <td>primitive 실행 중 허용되는 Mobility State입니다.</td>
    </tr>
    <tr>
      <td><code>metadata.state.allowed.manipulation</code></td>
      <td>primitive 실행 중 허용되는 Manipulation State입니다.</td>
    </tr>
    <tr>
      <td><code>metadata.state.allowed.power</code></td>
      <td>primitive 실행 중 허용되는 Power State입니다.</td>
    </tr>
    <tr>
      <td><code>metadata.state.effects.on_start</code></td>
      <td>primitive 시작 시 적용되는 state effect입니다.</td>
    </tr>
    <tr>
      <td><code>metadata.state.effects.on_end</code></td>
      <td>primitive 종료 시 적용되는 state effect입니다.</td>
    </tr>
  </tbody>
</table>

`NAVIGATE_TO`는 시작 시 `mobility=NAVIGATING`, 종료 시 `mobility=STATIONARY`이 됩니다. `GRASP`, `LIFT`는 `manipulation=HOLDING`을 사용하고, `PLACE`, `RELEASE`는 내려놓는 동안 `PLACING`을 거쳐 종료 후 `FREE`로 돌아갑니다. 확인/기록 계열 primitive는 보통 `STATIONARY`이며, cargo 관련 manipulation state는 caller의 cargo event에 따라 유지됩니다.

## Primitive Registry와 Task Catalog의 관계

Primitive는 task catalog의 현재 workflow에 포함될 수도 있고, 아직 특정 task에 연결되지 않은 registry capability로 존재할 수도 있습니다. Task는 업무 목적을 가진 workflow이고, primitive는 그 workflow를 구성하거나 state transition, safety, recovery, context 갱신을 지원하는 재사용 가능한 실행 능력입니다.

따라서 primitive registry는 현재 task catalog보다 넓은 범위를 가질 수 있습니다. 현재 task에서 참조되는 primitive는 active primitive로 분류하고, 아직 task에 직접 연결되지 않았지만 custom task, incident recovery protocol, 도메인별 adapter에서 사용할 수 있는 primitive는 registry primitive로 유지합니다.

<table>
  <colgroup>
    <col style="width: 22%;" />
    <col style="width: 28%;" />
    <col style="width: 50%;" />
  </colgroup>
  <thead>
    <tr>
      <th>Primitive 유형</th>
      <th>예시</th>
      <th>역할</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Active primitive</td>
      <td><code>NAVIGATE_TO</code>, <code>GRASP</code>, <code>UPDATE_RECORD</code></td>
      <td>현재 task catalog의 `steps`에서 직접 참조되는 primitive입니다.</td>
    </tr>
    <tr>
      <td>Registry primitive</td>
      <td><code>SCAN_ENVIRONMENT</code>, <code>LOCALIZE_SELF</code>, <code>RECOVER_BALANCE</code></td>
      <td>현재 task에 직접 연결되지 않아도 HumanoidSim이 보유할 수 있는 기본 능력입니다.</td>
    </tr>
    <tr>
      <td>Recovery primitive</td>
      <td><code>MONITOR_FORCE</code>, <code>CHECK_PAYLOAD_STABILITY</code>, <code>CALIBRATE_SENSOR</code></td>
      <td>incident 발생 후 복구, 재시도, 안전 확인을 지원하는 primitive입니다.</td>
    </tr>
    <tr>
      <td>Context primitive</td>
      <td><code>UPDATE_MAP_CONTEXT</code>, <code>REQUEST_CLEARANCE</code></td>
      <td>환경 정보, permission, map/context 동기화를 지원하는 primitive입니다.</td>
    </tr>
  </tbody>
</table>

비-task 성격 primitive는 특정 업무 목표를 직접 완결하지 않더라도, task 실행의 안정성, 관찰성, 복구 가능성을 높이는 기본 능력으로 정의할 수 있습니다. 이들은 task가 아니라도 primitive registry에 포함될 수 있으며, 필요 시 composite task나 incident recovery protocol에서 참조합니다.

## Primitive Grouping

Primitive는 task category가 아니라 휴머노이드 기능 축을 기준으로 그룹화합니다. Task category는 업무 도메인을 설명하고, primitive group은 휴머노이드가 수행하는 저수준 능력과 state 변화 방식을 설명합니다. 현재 registry primitive는 아래 9개 그룹 중 하나에 반드시 속합니다.

<table>
  <colgroup>
    <col style="width: 8%;" />
    <col style="width: 18%;" />
    <col style="width: 25%;" />
    <col style="width: 19%;" />
    <col style="width: 30%;" />
  </colgroup>
  <thead>
    <tr>
      <th>Group ID</th>
      <th>Group</th>
      <th>범위</th>
      <th>대표 State 영향</th>
      <th>Primitive</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>P01</td>
      <td>Mobility &amp; Spatial Alignment</td>
      <td>이동, 경로 추종, 위치 보정, docking, 자세 정렬</td>
      <td>`mobility=NAVIGATING` 또는 `DOCKING`</td>
      <td><code>ALIGN</code>, <code>NAVIGATE_TO</code>, <code>PARK_OR_RELEASE_VEHICLE</code></td>
    </tr>
    <tr>
      <td>P02</td>
      <td>Perception &amp; Identification</td>
      <td>대상 탐지, 식별, marker/label 판독, pose 추정</td>
      <td>대개 `STATIONARY`, 조작 state는 유지</td>
      <td><code>IDENTIFY_PRODUCT</code>, <code>LOCALIZE_COMPONENTS</code>, <code>LOCALIZE_OBJECT</code>, <code>LOCALIZE_PART</code>, <code>LOCALIZE_SURFACE</code>, <code>PRIMITIVE_IDENTIFY_ITEM</code></td>
    </tr>
    <tr>
      <td>P03</td>
      <td>Manipulation &amp; Payload</td>
      <td>팔/그리퍼 접근, 파지, 들기, 놓기, payload 안정성 확인</td>
      <td>`REACHING`, `HOLDING`, `PLACING`</td>
      <td><code>FIX_OR_HOLD_PART</code>, <code>GRASP</code>, <code>LIFT</code>, <code>PLACE</code>, <code>REACH_TO</code>, <code>RELEASE</code></td>
    </tr>
    <tr>
      <td>P04</td>
      <td>Safety &amp; Interaction</td>
      <td>안전 구역 확인, 의도 알림, 협업 readiness 확인, clearance 요청</td>
      <td>`WAITING` 또는 `EXECUTING` 중 safety reason과 연결 가능</td>
      <td><code>ANNOUNCE_INTENT</code>, <code>CHECK_SAFETY_ZONE</code>, <code>CONFIRM_OPERATOR_STATE</code>, <code>EXECUTE_HUMAN_COLLABORATION_ACTION</code>, <code>VERIFY_AUTHORIZATION</code>, <code>VERIFY_LOCKOUT_IF_REQUIRED</code></td>
    </tr>
    <tr>
      <td>P05</td>
      <td>Equipment &amp; Tool Operation</td>
      <td>설비, tool, dispenser, system action 실행</td>
      <td>주로 `STATIONARY`, task context에 따라 manipulation 유지</td>
      <td><code>EXECUTE_ASSEMBLY_ACTION</code>, <code>EXECUTE_EHS_ACTION</code>, <code>EXECUTE_MACHINE_ACTION</code>, <code>EXECUTE_PACKAGING_ACTION</code>, <code>EXECUTE_SYSTEM_ACTION</code>, <code>OPERATE_TOOL</code>, <code>OPERATE_TOOL_OR_DISPENSER</code>, <code>PREPARE_PACKAGING</code>, <code>PRIMITIVE_APPLY_MATERIAL</code>, <code>PRIMITIVE_PREPARE_SURFACE</code>, <code>PROCESS_FEATURE_OR_SURFACE</code></td>
    </tr>
    <tr>
      <td>P06</td>
      <td>Verification &amp; Quality</td>
      <td>상태, 배치, 품질, 수량, 결과 검증 및 분류</td>
      <td>대개 `STATIONARY`, 결과에 따라 task branch 발생</td>
      <td><code>CLASSIFY_RESULT</code>, <code>EXECUTE_QUALITY_ACTION</code>, <code>INSPECT_AREA</code>, <code>INSPECT_RESULT</code>, <code>PRIMITIVE_VERIFY_ASSEMBLY</code>, <code>PRIMITIVE_VERIFY_PACKAGE</code>, <code>VERIFY_AREA_STATE</code>, <code>VERIFY_COVERAGE_OR_AMOUNT</code>, <code>VERIFY_MACHINE_STATE</code>, <code>VERIFY_PLACEMENT</code></td>
    </tr>
    <tr>
      <td>P07</td>
      <td>Records &amp; Digital Context</td>
      <td>record 생성/갱신, traceability, map/context 동기화</td>
      <td>물리 state 변화는 작고 context 갱신 중심</td>
      <td><code>CHECK_CONTEXT</code>, <code>CREATE_OR_UPDATE_RECORD</code>, <code>LOG_RESULT</code>, <code>READ_CONTEXT</code>, <code>RECORD_RESULT</code>, <code>REPORT_RESULT</code>, <code>UPDATE_RECORD</code>, <code>VERIFY_TRANSACTION</code></td>
    </tr>
    <tr>
      <td>P08</td>
      <td>Recovery &amp; Self-Maintenance</td>
      <td>self check, diagnostics, sensor calibration, fault containment</td>
      <td>`BLOCKED` 또는 `DISABLED` 이후 recovery protocol에서 사용</td>
      <td><code>EXECUTE_MAINTENANCE_ACTION</code>, <code>INSPECT_OR_DIAGNOSE</code>, <code>READ_MACHINE_STATE</code>, <code>VERIFY_ROBOT_STATE</code></td>
    </tr>
    <tr>
      <td>P09</td>
      <td>Resource &amp; Inventory Interface</td>
      <td>요청 확인, 재고 수량 검증, warehouse/resource action</td>
      <td>resource incident와 연결되기 쉬움</td>
      <td><code>CHECK_REQUEST</code>, <code>EXECUTE_WAREHOUSE_ACTION</code>, <code>PRIMITIVE_UPDATE_INVENTORY_RECORD</code>, <code>VERIFY_LEVEL_OR_QUANTITY</code>, <code>VERIFY_RECORD</code></td>
    </tr>
  </tbody>
</table>

비-task 성격 확장 후보는 아래처럼 같은 group 체계에 배치합니다. 이 목록은 아직 registry에 등록된 primitive가 아니라, 향후 `data/primitives/*.json`에 추가할 수 있는 후보입니다.

<table>
  <colgroup>
    <col style="width: 8%;" />
    <col style="width: 24%;" />
    <col style="width: 68%;" />
  </colgroup>
  <thead>
    <tr>
      <th>Group ID</th>
      <th>Group</th>
      <th>확장 후보 Primitive</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>P01</td>
      <td>Mobility &amp; Spatial Alignment</td>
      <td><code>LOCALIZE_SELF</code>, <code>FOLLOW_PATH_SEGMENT</code>, <code>RECOVER_POSITION</code></td>
    </tr>
    <tr>
      <td>P02</td>
      <td>Perception &amp; Identification</td>
      <td><code>SCAN_ENVIRONMENT</code>, <code>ESTIMATE_POSE</code>, <code>READ_MARKER</code></td>
    </tr>
    <tr>
      <td>P03</td>
      <td>Manipulation &amp; Payload</td>
      <td><code>PLAN_GRASP</code>, <code>MONITOR_FORCE</code>, <code>CHECK_PAYLOAD_STABILITY</code></td>
    </tr>
    <tr>
      <td>P04</td>
      <td>Safety &amp; Interaction</td>
      <td><code>REQUEST_CLEARANCE</code>, <code>YIELD_TO_TRAFFIC</code>, <code>WAIT_FOR_OPERATOR_READY</code></td>
    </tr>
    <tr>
      <td>P05</td>
      <td>Equipment &amp; Tool Operation</td>
      <td><code>SELECT_TOOL</code>, <code>CONFIGURE_TOOL</code>, <code>CHANGE_TOOL_MODE</code></td>
    </tr>
    <tr>
      <td>P06</td>
      <td>Verification &amp; Quality</td>
      <td><code>COMPARE_MEASUREMENT</code>, <code>VALIDATE_RESULT</code>, <code>SAMPLE_SENSOR_READING</code></td>
    </tr>
    <tr>
      <td>P07</td>
      <td>Records &amp; Digital Context</td>
      <td><code>UPDATE_MAP_CONTEXT</code>, <code>SYNC_WORK_CONTEXT</code>, <code>CACHE_OBSERVATION</code></td>
    </tr>
    <tr>
      <td>P08</td>
      <td>Recovery &amp; Self-Maintenance</td>
      <td><code>CALIBRATE_SENSOR</code>, <code>RECOVER_BALANCE</code>, <code>RUN_DIAGNOSTIC_PROBE</code></td>
    </tr>
    <tr>
      <td>P09</td>
      <td>Resource &amp; Inventory Interface</td>
      <td><code>RESERVE_RESOURCE</code>, <code>RELEASE_RESOURCE</code>, <code>REFRESH_INVENTORY_VIEW</code></td>
    </tr>
  </tbody>
</table>

권장 schema는 primitive JSON의 `metadata.group`에 `group_id`, `group_name`, `capability_axis`, `state_axes`를 추가하는 방식입니다. 이렇게 하면 task reference와 runtime executor가 primitive를 임의로 묶지 않고 HumanoidSim 정의를 그대로 사용할 수 있습니다.

## Primitive 목록

<table>
  <colgroup>
    <col style="width: 10%;" />
    <col style="width: 10%;" />
    <col style="width: 23%;" />
    <col style="width: 8%;" />
    <col style="width: 10%;" />
    <col style="width: 10%;" />
    <col style="width: 8%;" />
    <col style="width: 6%;" />
    <col style="width: 10%;" />
    <col style="width: 5%;" />
  </colgroup>
  <thead>
    <tr>
      <th>Code</th>
      <th>Group</th>
      <th>설명</th>
      <th>Availability State</th>
      <th>Mobility State</th>
      <th>Manipulation State</th>
      <th>입력</th>
      <th>출력</th>
      <th>사용 Task</th>
      <th>원본</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>ALIGN</code></td>
      <td>P01<br>Mobility &amp; Spatial Alignment</td>
      <td>설비, 충전기, 작업대 또는 대상 위치에 정렬하거나 docking합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>DOCKING</code> / 종료 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CONNECT_COMPONENT</code><br><code>DISCONNECT_COMPONENT</code><br><code>FASTEN_COMPONENT</code><br><code>INSERT_COMPONENT</code><br><code>REMOVE_COMPONENT</code><br><code>UNFASTEN_COMPONENT</code></td>
      <td><code>data/primitives/ALIGN.json</code></td>
    </tr>
    <tr>
      <td><code>ANNOUNCE_INTENT</code></td>
      <td>P04<br>Safety &amp; Interaction</td>
      <td>handover나 공동 작업 전에 의도와 다음 행동을 알립니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>HANDOVER_ITEM</code><br><code>HANDOVER_TOOL</code><br><code>HOLD_OR_POSITION_FOR_OPERATOR</code><br><code>RECEIVE_FROM_OPERATOR</code></td>
      <td><code>data/primitives/ANNOUNCE_INTENT.json</code></td>
    </tr>
    <tr>
      <td><code>CHECK_CONTEXT</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>요청, context, 안전 조건 또는 사전 조건을 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CALIBRATE_ROBOT</code><br><code>CHANGE_END_EFFECTOR</code><br><code>INITIALIZE_ROBOT</code><br><code>LOAD_WORK_CONTEXT</code><br><code>MANAGE_ROBOT_POWER</code><br><code>RECOVER_FROM_FAULT</code><br><code>SELF_CHECK</code><br><code>SET_OPERATION_MODE</code></td>
      <td><code>data/primitives/CHECK_CONTEXT.json</code></td>
    </tr>
    <tr>
      <td><code>CHECK_REQUEST</code></td>
      <td>P09<br>Resource &amp; Inventory Interface</td>
      <td>요청, context, 안전 조건 또는 사전 조건을 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>REMOVE_MATERIAL</code><br><code>REPLENISH_MATERIAL</code></td>
      <td><code>data/primitives/CHECK_REQUEST.json</code></td>
    </tr>
    <tr>
      <td><code>CHECK_SAFETY_ZONE</code></td>
      <td>P04<br>Safety &amp; Interaction</td>
      <td>요청, context, 안전 조건 또는 사전 조건을 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CHANGE_MACHINE_CONFIGURATION</code><br><code>CLEAR_MACHINE_FAULT</code><br><code>CONTROL_MACHINE_CYCLE</code><br><code>DIAGNOSE_MACHINE</code><br><code>INSPECT_MACHINE</code><br><code>LOAD_MACHINE</code><br><code>OPERATE_MACHINE_INTERFACE</code><br><code>PREVENTIVE_MAINTENANCE</code><br><code>REPAIR_MACHINE</code><br><code>REPLACE_MACHINE_PART</code><br><code>SETUP_MACHINE</code><br><code>UNLOAD_MACHINE</code></td>
      <td><code>data/primitives/CHECK_SAFETY_ZONE.json</code></td>
    </tr>
    <tr>
      <td><code>CLASSIFY_RESULT</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>IDENTIFY_ITEM</code><br><code>INSPECT_PRODUCT</code><br><code>MEASURE_FEATURE</code><br><code>VERIFY_ASSEMBLY</code><br><code>VERIFY_PACKAGE</code></td>
      <td><code>data/primitives/CLASSIFY_RESULT.json</code></td>
    </tr>
    <tr>
      <td><code>CONFIRM_OPERATOR_STATE</code></td>
      <td>P04<br>Safety &amp; Interaction</td>
      <td>operator 또는 협업 대상의 준비 상태와 안전 상태를 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>HANDOVER_ITEM</code><br><code>HANDOVER_TOOL</code><br><code>HOLD_OR_POSITION_FOR_OPERATOR</code><br><code>RECEIVE_FROM_OPERATOR</code></td>
      <td><code>data/primitives/CONFIRM_OPERATOR_STATE.json</code></td>
    </tr>
    <tr>
      <td><code>CREATE_OR_UPDATE_RECORD</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>작업 결과, traceability, 재고 또는 예외 정보를 기록하거나 갱신합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CAPTURE_EVIDENCE_OR_STATUS</code><br><code>COMPLETE_WORK_ORDER</code><br><code>CREATE_EXCEPTION_REPORT</code><br><code>RECORD_QUALITY_RESULT</code><br><code>REGISTER_TRACEABILITY</code><br><code>REPORT_HAZARD</code><br><code>REPORT_OPERATION_RESULT</code><br><code>START_WORK_ORDER</code><br><code>UPDATE_INVENTORY_RECORD</code></td>
      <td><code>data/primitives/CREATE_OR_UPDATE_RECORD.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_ASSEMBLY_ACTION</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CONNECT_COMPONENT</code><br><code>DISCONNECT_COMPONENT</code><br><code>FASTEN_COMPONENT</code><br><code>INSERT_COMPONENT</code><br><code>REMOVE_COMPONENT</code><br><code>UNFASTEN_COMPONENT</code></td>
      <td><code>data/primitives/EXECUTE_ASSEMBLY_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_EHS_ACTION</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CLEAN_ASSET</code></td>
      <td><code>data/primitives/EXECUTE_EHS_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_HUMAN_COLLABORATION_ACTION</code></td>
      <td>P04<br>Safety &amp; Interaction</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>HANDOVER_ITEM</code><br><code>HANDOVER_TOOL</code><br><code>HOLD_OR_POSITION_FOR_OPERATOR</code><br><code>RECEIVE_FROM_OPERATOR</code></td>
      <td><code>data/primitives/EXECUTE_HUMAN_COLLABORATION_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_MACHINE_ACTION</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CONTROL_MACHINE_CYCLE</code><br><code>LOAD_MACHINE</code><br><code>OPERATE_MACHINE_INTERFACE</code><br><code>UNLOAD_MACHINE</code></td>
      <td><code>data/primitives/EXECUTE_MACHINE_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_MAINTENANCE_ACTION</code></td>
      <td>P08<br>Recovery &amp; Self-Maintenance</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CALIBRATE_MACHINE</code><br><code>REPAIR_MACHINE</code><br><code>REPLACE_MACHINE_PART</code><br><code>SERVICE_FLUID_OR_LUBRICATION</code></td>
      <td><code>data/primitives/EXECUTE_MAINTENANCE_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_PACKAGING_ACTION</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>LABEL_ITEM_OR_PACKAGE</code></td>
      <td><code>data/primitives/EXECUTE_PACKAGING_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_QUALITY_ACTION</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>IDENTIFY_ITEM</code><br><code>INSPECT_PRODUCT</code><br><code>MEASURE_FEATURE</code><br><code>VERIFY_ASSEMBLY</code><br><code>VERIFY_PACKAGE</code></td>
      <td><code>data/primitives/EXECUTE_QUALITY_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_SYSTEM_ACTION</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CALIBRATE_ROBOT</code><br><code>CHANGE_END_EFFECTOR</code><br><code>INITIALIZE_ROBOT</code><br><code>LOAD_WORK_CONTEXT</code><br><code>MANAGE_ROBOT_POWER</code><br><code>RECOVER_FROM_FAULT</code><br><code>SELF_CHECK</code><br><code>SET_OPERATION_MODE</code></td>
      <td><code>data/primitives/EXECUTE_SYSTEM_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>EXECUTE_WAREHOUSE_ACTION</code></td>
      <td>P09<br>Resource &amp; Inventory Interface</td>
      <td>task context에 맞는 domain action을 수행합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>COUNT_INVENTORY</code></td>
      <td><code>data/primitives/EXECUTE_WAREHOUSE_ACTION.json</code></td>
    </tr>
    <tr>
      <td><code>FIX_OR_HOLD_PART</code></td>
      <td>P03<br>Manipulation &amp; Payload</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CREATE_FEATURE</code><br><code>CUT_OR_TRIM_MATERIAL</code><br><code>FINISH_SURFACE</code><br><code>MARK_PART</code><br><code>REMOVE_BURR_OR_FLASH</code></td>
      <td><code>data/primitives/FIX_OR_HOLD_PART.json</code></td>
    </tr>
    <tr>
      <td><code>GRASP</code></td>
      <td>P03<br>Manipulation &amp; Payload</td>
      <td>대상 item이나 tool을 잡거나 지지합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>시작 <code>HOLDING</code> / 종료 <code>HOLDING</code></td>
      <td>item: Any</td>
      <td>result: dict</td>
      <td><code>CONNECT_COMPONENT</code><br><code>DISCONNECT_COMPONENT</code><br><code>FASTEN_COMPONENT</code><br><code>INSERT_COMPONENT</code><br><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>REMOVE_COMPONENT</code><br><code>TRANSFER</code><br><code>UNFASTEN_COMPONENT</code></td>
      <td><code>data/primitives/GRASP.json</code></td>
    </tr>
    <tr>
      <td><code>IDENTIFY_PRODUCT</code></td>
      <td>P02<br>Perception &amp; Identification</td>
      <td>대상 item, 제품, 부품 또는 label의 정체를 식별합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>LABEL_ITEM_OR_PACKAGE</code></td>
      <td><code>data/primitives/IDENTIFY_PRODUCT.json</code></td>
    </tr>
    <tr>
      <td><code>INSPECT_AREA</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CLEAN_ASSET</code></td>
      <td><code>data/primitives/INSPECT_AREA.json</code></td>
    </tr>
    <tr>
      <td><code>INSPECT_OR_DIAGNOSE</code></td>
      <td>P08<br>Recovery &amp; Self-Maintenance</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>INSPECT_MACHINE</code></td>
      <td><code>data/primitives/INSPECT_OR_DIAGNOSE.json</code></td>
    </tr>
    <tr>
      <td><code>INSPECT_RESULT</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CREATE_FEATURE</code><br><code>CUT_OR_TRIM_MATERIAL</code><br><code>FINISH_SURFACE</code><br><code>MARK_PART</code><br><code>REMOVE_BURR_OR_FLASH</code></td>
      <td><code>data/primitives/INSPECT_RESULT.json</code></td>
    </tr>
    <tr>
      <td><code>LIFT</code></td>
      <td>P03<br>Manipulation &amp; Payload</td>
      <td>잡은 대상을 들어 운반 가능한 상태로 만듭니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>시작 <code>HOLDING</code> / 종료 <code>HOLDING</code></td>
      <td>item: Any</td>
      <td>result: dict</td>
      <td><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>TRANSFER</code></td>
      <td><code>data/primitives/LIFT.json</code></td>
    </tr>
    <tr>
      <td><code>LOCALIZE_COMPONENTS</code></td>
      <td>P02<br>Perception &amp; Identification</td>
      <td>대상 객체, 부품, 표면 또는 영역의 위치와 접근 정보를 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CONNECT_COMPONENT</code><br><code>DISCONNECT_COMPONENT</code><br><code>FASTEN_COMPONENT</code><br><code>INSERT_COMPONENT</code><br><code>REMOVE_COMPONENT</code><br><code>UNFASTEN_COMPONENT</code></td>
      <td><code>data/primitives/LOCALIZE_COMPONENTS.json</code></td>
    </tr>
    <tr>
      <td><code>LOCALIZE_OBJECT</code></td>
      <td>P02<br>Perception &amp; Identification</td>
      <td>대상 객체, 부품, 표면 또는 영역의 위치와 접근 정보를 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>item: Any</td>
      <td>result: dict</td>
      <td><code>IDENTIFY_ITEM</code><br><code>INSPECT_PRODUCT</code><br><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>MEASURE_FEATURE</code><br><code>TRANSFER</code><br><code>VERIFY_ASSEMBLY</code><br><code>VERIFY_PACKAGE</code></td>
      <td><code>data/primitives/LOCALIZE_OBJECT.json</code></td>
    </tr>
    <tr>
      <td><code>LOCALIZE_PART</code></td>
      <td>P02<br>Perception &amp; Identification</td>
      <td>대상 객체, 부품, 표면 또는 영역의 위치와 접근 정보를 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CREATE_FEATURE</code><br><code>CUT_OR_TRIM_MATERIAL</code><br><code>FINISH_SURFACE</code><br><code>MARK_PART</code><br><code>REMOVE_BURR_OR_FLASH</code></td>
      <td><code>data/primitives/LOCALIZE_PART.json</code></td>
    </tr>
    <tr>
      <td><code>LOCALIZE_SURFACE</code></td>
      <td>P02<br>Perception &amp; Identification</td>
      <td>대상 객체, 부품, 표면 또는 영역의 위치와 접근 정보를 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>APPLY_MATERIAL</code><br><code>PREPARE_SURFACE</code><br><code>REMOVE_APPLIED_MATERIAL</code><br><code>VERIFY_MATERIAL_APPLICATION</code></td>
      <td><code>data/primitives/LOCALIZE_SURFACE.json</code></td>
    </tr>
    <tr>
      <td><code>LOG_RESULT</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>작업 결과, traceability, 재고 또는 예외 정보를 기록하거나 갱신합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CALIBRATE_MACHINE</code><br><code>CALIBRATE_ROBOT</code><br><code>CAPTURE_EVIDENCE_OR_STATUS</code><br><code>CHANGE_END_EFFECTOR</code><br><code>CHANGE_MACHINE_CONFIGURATION</code><br><code>CLEAR_MACHINE_FAULT</code><br><code>COMPLETE_WORK_ORDER</code><br><code>CONTROL_MACHINE_CYCLE</code><br><code>CREATE_EXCEPTION_REPORT</code><br><code>DIAGNOSE_MACHINE</code><br><code>HANDOVER_ITEM</code><br><code>HANDOVER_TOOL</code><br><code>HOLD_OR_POSITION_FOR_OPERATOR</code><br><code>INITIALIZE_ROBOT</code><br><code>INSPECT_MACHINE</code><br><code>LOAD_MACHINE</code><br><code>LOAD_WORK_CONTEXT</code><br><code>MANAGE_ROBOT_POWER</code><br><code>OPERATE_MACHINE_INTERFACE</code><br><code>PREVENTIVE_MAINTENANCE</code><br><code>RECEIVE_FROM_OPERATOR</code><br><code>RECORD_QUALITY_RESULT</code><br><code>RECOVER_FROM_FAULT</code><br><code>REGISTER_TRACEABILITY</code><br><code>REPAIR_MACHINE</code><br><code>REPLACE_MACHINE_PART</code><br><code>REPORT_HAZARD</code><br><code>REPORT_OPERATION_RESULT</code><br><code>SELF_CHECK</code><br><code>SERVICE_FLUID_OR_LUBRICATION</code><br><code>SETUP_MACHINE</code><br><code>SET_OPERATION_MODE</code><br><code>START_WORK_ORDER</code><br><code>UNLOAD_MACHINE</code><br><code>UPDATE_INVENTORY_RECORD</code></td>
      <td><code>data/primitives/LOG_RESULT.json</code></td>
    </tr>
    <tr>
      <td><code>NAVIGATE_TO</code></td>
      <td>P01<br>Mobility &amp; Spatial Alignment</td>
      <td>목표 위치나 대상의 service tile까지 이동합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>NAVIGATING</code> / 종료 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>area: Any<br>destination: Any<br>machine: Any<br>operator: Any<br>source: Any</td>
      <td>result: dict</td>
      <td><code>CLEAN_ASSET</code><br><code>CONTROL_MACHINE_CYCLE</code><br><code>HANDOVER_ITEM</code><br><code>HANDOVER_TOOL</code><br><code>HOLD_OR_POSITION_FOR_OPERATOR</code><br><code>LOAD_MACHINE</code><br><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>OPERATE_MACHINE_INTERFACE</code><br><code>RECEIVE_FROM_OPERATOR</code><br><code>TRANSFER</code><br><code>UNLOAD_MACHINE</code></td>
      <td><code>data/primitives/NAVIGATE_TO.json</code></td>
    </tr>
    <tr>
      <td><code>OPERATE_TOOL</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>tool, dispenser, interface 또는 장치를 조작합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CREATE_FEATURE</code><br><code>CUT_OR_TRIM_MATERIAL</code><br><code>FINISH_SURFACE</code><br><code>MARK_PART</code><br><code>REMOVE_BURR_OR_FLASH</code></td>
      <td><code>data/primitives/OPERATE_TOOL.json</code></td>
    </tr>
    <tr>
      <td><code>OPERATE_TOOL_OR_DISPENSER</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>tool, dispenser, interface 또는 장치를 조작합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>APPLY_MATERIAL</code><br><code>PREPARE_SURFACE</code><br><code>REMOVE_APPLIED_MATERIAL</code><br><code>VERIFY_MATERIAL_APPLICATION</code></td>
      <td><code>data/primitives/OPERATE_TOOL_OR_DISPENSER.json</code></td>
    </tr>
    <tr>
      <td><code>PARK_OR_RELEASE_VEHICLE</code></td>
      <td>P01<br>Mobility &amp; Spatial Alignment</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>OPERATE_VEHICLE_TRANSPORT</code></td>
      <td><code>data/primitives/PARK_OR_RELEASE_VEHICLE.json</code></td>
    </tr>
    <tr>
      <td><code>PLACE</code></td>
      <td>P03<br>Manipulation &amp; Payload</td>
      <td>운반 중인 대상을 목표 위치에 내려놓습니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>시작 <code>PLACING</code> / 종료 <code>FREE</code></td>
      <td>destination_pose: Any<br>item: Any</td>
      <td>result: dict</td>
      <td><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>TRANSFER</code></td>
      <td><code>data/primitives/PLACE.json</code></td>
    </tr>
    <tr>
      <td><code>PREPARE_PACKAGING</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>LABEL_ITEM_OR_PACKAGE</code></td>
      <td><code>data/primitives/PREPARE_PACKAGING.json</code></td>
    </tr>
    <tr>
      <td><code>PRIMITIVE_APPLY_MATERIAL</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>APPLY_MATERIAL</code><br><code>PREPARE_SURFACE</code><br><code>REMOVE_APPLIED_MATERIAL</code><br><code>VERIFY_MATERIAL_APPLICATION</code></td>
      <td><code>data/primitives/PRIMITIVE_APPLY_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code></td>
      <td>P02<br>Perception &amp; Identification</td>
      <td>대상 item, 제품, 부품 또는 label의 정체를 식별합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>COUNT_INVENTORY</code><br><code>IDENTIFY_ITEM</code><br><code>INSPECT_PRODUCT</code><br><code>MEASURE_FEATURE</code><br><code>REMOVE_MATERIAL</code><br><code>REPLENISH_MATERIAL</code><br><code>VERIFY_ASSEMBLY</code><br><code>VERIFY_PACKAGE</code></td>
      <td><code>data/primitives/PRIMITIVE_IDENTIFY_ITEM.json</code></td>
    </tr>
    <tr>
      <td><code>PRIMITIVE_PREPARE_SURFACE</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>APPLY_MATERIAL</code><br><code>PREPARE_SURFACE</code><br><code>REMOVE_APPLIED_MATERIAL</code><br><code>VERIFY_MATERIAL_APPLICATION</code></td>
      <td><code>data/primitives/PRIMITIVE_PREPARE_SURFACE.json</code></td>
    </tr>
    <tr>
      <td><code>PRIMITIVE_UPDATE_INVENTORY_RECORD</code></td>
      <td>P09<br>Resource &amp; Inventory Interface</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>COUNT_INVENTORY</code></td>
      <td><code>data/primitives/PRIMITIVE_UPDATE_INVENTORY_RECORD.json</code></td>
    </tr>
    <tr>
      <td><code>PRIMITIVE_VERIFY_ASSEMBLY</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CONNECT_COMPONENT</code><br><code>DISCONNECT_COMPONENT</code><br><code>FASTEN_COMPONENT</code><br><code>INSERT_COMPONENT</code><br><code>REMOVE_COMPONENT</code><br><code>UNFASTEN_COMPONENT</code></td>
      <td><code>data/primitives/PRIMITIVE_VERIFY_ASSEMBLY.json</code></td>
    </tr>
    <tr>
      <td><code>PRIMITIVE_VERIFY_PACKAGE</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>LABEL_ITEM_OR_PACKAGE</code></td>
      <td><code>data/primitives/PRIMITIVE_VERIFY_PACKAGE.json</code></td>
    </tr>
    <tr>
      <td><code>PROCESS_FEATURE_OR_SURFACE</code></td>
      <td>P05<br>Equipment &amp; Tool Operation</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CREATE_FEATURE</code><br><code>CUT_OR_TRIM_MATERIAL</code><br><code>FINISH_SURFACE</code><br><code>MARK_PART</code><br><code>REMOVE_BURR_OR_FLASH</code></td>
      <td><code>data/primitives/PROCESS_FEATURE_OR_SURFACE.json</code></td>
    </tr>
    <tr>
      <td><code>REACH_TO</code></td>
      <td>P03<br>Manipulation &amp; Payload</td>
      <td>대상 item이나 tool에 팔 또는 gripper를 접근시킵니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>시작 <code>REACHING</code> / 종료 <code>FREE</code></td>
      <td>item: Any</td>
      <td>result: dict</td>
      <td><code>CONNECT_COMPONENT</code><br><code>DISCONNECT_COMPONENT</code><br><code>FASTEN_COMPONENT</code><br><code>INSERT_COMPONENT</code><br><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>REMOVE_COMPONENT</code><br><code>TRANSFER</code><br><code>UNFASTEN_COMPONENT</code></td>
      <td><code>data/primitives/REACH_TO.json</code></td>
    </tr>
    <tr>
      <td><code>READ_CONTEXT</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>설비, 시스템 또는 작업 맥락의 현재 상태를 읽습니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CAPTURE_EVIDENCE_OR_STATUS</code><br><code>COMPLETE_WORK_ORDER</code><br><code>CREATE_EXCEPTION_REPORT</code><br><code>RECORD_QUALITY_RESULT</code><br><code>REGISTER_TRACEABILITY</code><br><code>REPORT_HAZARD</code><br><code>REPORT_OPERATION_RESULT</code><br><code>START_WORK_ORDER</code><br><code>UPDATE_INVENTORY_RECORD</code></td>
      <td><code>data/primitives/READ_CONTEXT.json</code></td>
    </tr>
    <tr>
      <td><code>READ_MACHINE_STATE</code></td>
      <td>P08<br>Recovery &amp; Self-Maintenance</td>
      <td>설비, 시스템 또는 작업 맥락의 현재 상태를 읽습니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CONTROL_MACHINE_CYCLE</code><br><code>LOAD_MACHINE</code><br><code>OPERATE_MACHINE_INTERFACE</code><br><code>SETUP_MACHINE</code><br><code>UNLOAD_MACHINE</code></td>
      <td><code>data/primitives/READ_MACHINE_STATE.json</code></td>
    </tr>
    <tr>
      <td><code>RECORD_RESULT</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>작업 결과, traceability, 재고 또는 예외 정보를 기록하거나 갱신합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>APPLY_MATERIAL</code><br><code>CREATE_FEATURE</code><br><code>CURE_MATERIAL</code><br><code>CUT_OR_TRIM_MATERIAL</code><br><code>FINISH_SURFACE</code><br><code>IDENTIFY_ITEM</code><br><code>INSPECT_PRODUCT</code><br><code>LABEL_ITEM_OR_PACKAGE</code><br><code>MARK_PART</code><br><code>MEASURE_FEATURE</code><br><code>PREPARE_SURFACE</code><br><code>REMOVE_APPLIED_MATERIAL</code><br><code>REMOVE_BURR_OR_FLASH</code><br><code>VERIFY_ASSEMBLY</code><br><code>VERIFY_MATERIAL_APPLICATION</code><br><code>VERIFY_PACKAGE</code></td>
      <td><code>data/primitives/RECORD_RESULT.json</code></td>
    </tr>
    <tr>
      <td><code>RELEASE</code></td>
      <td>P03<br>Manipulation &amp; Payload</td>
      <td>잡고 있던 대상이나 tool을 놓습니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>시작 <code>PLACING</code> / 종료 <code>FREE</code></td>
      <td>item: Any</td>
      <td>result: dict</td>
      <td><code>CONNECT_COMPONENT</code><br><code>DISCONNECT_COMPONENT</code><br><code>FASTEN_COMPONENT</code><br><code>INSERT_COMPONENT</code><br><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>REMOVE_COMPONENT</code><br><code>TRANSFER</code><br><code>UNFASTEN_COMPONENT</code></td>
      <td><code>data/primitives/RELEASE.json</code></td>
    </tr>
    <tr>
      <td><code>REPORT_RESULT</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>task context에 따라 사용되는 휴머노이드 primitive skill입니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CLEAN_AREA</code><br><code>CLEAN_ASSET</code></td>
      <td><code>data/primitives/REPORT_RESULT.json</code></td>
    </tr>
    <tr>
      <td><code>UPDATE_RECORD</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>작업 결과, traceability, 재고 또는 예외 정보를 기록하거나 갱신합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>REMOVE_MATERIAL</code><br><code>REPLENISH_MATERIAL</code></td>
      <td><code>data/primitives/UPDATE_RECORD.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_AREA_STATE</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CLEAN_AREA</code><br><code>CLEAN_ASSET</code></td>
      <td><code>data/primitives/VERIFY_AREA_STATE.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_AUTHORIZATION</code></td>
      <td>P04<br>Safety &amp; Interaction</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>OPERATE_VEHICLE_TRANSPORT</code></td>
      <td><code>data/primitives/VERIFY_AUTHORIZATION.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_COVERAGE_OR_AMOUNT</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>APPLY_MATERIAL</code><br><code>PREPARE_SURFACE</code><br><code>REMOVE_APPLIED_MATERIAL</code><br><code>VERIFY_MATERIAL_APPLICATION</code></td>
      <td><code>data/primitives/VERIFY_COVERAGE_OR_AMOUNT.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_LEVEL_OR_QUANTITY</code></td>
      <td>P09<br>Resource &amp; Inventory Interface</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>REMOVE_MATERIAL</code><br><code>REPLENISH_MATERIAL</code></td>
      <td><code>data/primitives/VERIFY_LEVEL_OR_QUANTITY.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_LOCKOUT_IF_REQUIRED</code></td>
      <td>P04<br>Safety &amp; Interaction</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>INSPECT_MACHINE</code></td>
      <td><code>data/primitives/VERIFY_LOCKOUT_IF_REQUIRED.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_MACHINE_STATE</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CALIBRATE_MACHINE</code><br><code>CHANGE_MACHINE_CONFIGURATION</code><br><code>CLEAR_MACHINE_FAULT</code><br><code>CONTROL_MACHINE_CYCLE</code><br><code>LOAD_MACHINE</code><br><code>OPERATE_MACHINE_INTERFACE</code><br><code>REPAIR_MACHINE</code><br><code>REPLACE_MACHINE_PART</code><br><code>SERVICE_FLUID_OR_LUBRICATION</code><br><code>SETUP_MACHINE</code><br><code>UNLOAD_MACHINE</code></td>
      <td><code>data/primitives/VERIFY_MACHINE_STATE.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_PLACEMENT</code></td>
      <td>P06<br>Verification &amp; Quality</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>item: Any</td>
      <td>result: dict</td>
      <td><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code><br><code>OPERATE_VEHICLE_TRANSPORT</code><br><code>TRANSFER</code></td>
      <td><code>data/primitives/VERIFY_PLACEMENT.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_RECORD</code></td>
      <td>P09<br>Resource &amp; Inventory Interface</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>COUNT_INVENTORY</code></td>
      <td><code>data/primitives/VERIFY_RECORD.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_ROBOT_STATE</code></td>
      <td>P08<br>Recovery &amp; Self-Maintenance</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CALIBRATE_ROBOT</code><br><code>CHANGE_END_EFFECTOR</code><br><code>INITIALIZE_ROBOT</code><br><code>LOAD_WORK_CONTEXT</code><br><code>MANAGE_ROBOT_POWER</code><br><code>RECOVER_FROM_FAULT</code><br><code>SELF_CHECK</code><br><code>SET_OPERATION_MODE</code></td>
      <td><code>data/primitives/VERIFY_ROBOT_STATE.json</code></td>
    </tr>
    <tr>
      <td><code>VERIFY_TRANSACTION</code></td>
      <td>P07<br>Records &amp; Digital Context</td>
      <td>작업 조건, 배치, 상태 또는 결과가 기준에 맞는지 확인합니다.</td>
      <td><code>EXECUTING</code></td>
      <td>시작 <code>STATIONARY</code></td>
      <td>상황 의존: <code>FREE</code>, <code>REACHING</code>, <code>HOLDING</code>, <code>PLACING</code></td>
      <td>-</td>
      <td>result: dict</td>
      <td><code>CAPTURE_EVIDENCE_OR_STATUS</code><br><code>COMPLETE_WORK_ORDER</code><br><code>CREATE_EXCEPTION_REPORT</code><br><code>RECORD_QUALITY_RESULT</code><br><code>REGISTER_TRACEABILITY</code><br><code>REPORT_HAZARD</code><br><code>REPORT_OPERATION_RESULT</code><br><code>START_WORK_ORDER</code><br><code>UPDATE_INVENTORY_RECORD</code></td>
      <td><code>data/primitives/VERIFY_TRANSACTION.json</code></td>
    </tr>
  </tbody>
</table>

## Primitive 추가/수정 방법

1. `data/primitives/<CODE>.json`을 추가하거나 수정합니다.
2. `metadata.state.availability.running`, `allowed`, `effects.on_start`, `effects.on_end`를 명시합니다.
3. `data/state_schema_core.json`의 `primitive_state_profiles`에도 같은 state profile을 반영합니다.
4. task에서 사용하려면 `data/tasks/*.json` step에 `call_code=<CODE>`, `expected_level=PRIMITIVE_SKILL`로 참조합니다.
5. `python -m unittest discover -s tests`로 primitive profile과 task hierarchy validation을 확인합니다.
