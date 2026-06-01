# Task Reference

## Generic Item Request

일부 task 입력의 `item`은 반드시 concrete item id일 필요가 없습니다. 예를 들어 `REPLENISH_MATERIAL`은 “특정 `MAT-WH-*`를 가져오라”가 아니라 “source에서 사용 가능한 material 하나를 찾아 destination을 target level까지 보충하라”는 generic request로 실행될 수 있습니다. 이 경우 task input은 `entity_type=material`, `selection_policy=available_material_from_source` 같은 request를 담고, concrete item instance는 `PRIMITIVE_IDENTIFY_ITEM` 단계에서 확정됩니다.

`LOAD_MACHINE`, `INSPECT_PRODUCT`, 일반 `TRANSFER`처럼 특정 queue item이나 machine output이 task 의미의 핵심인 경우에는 concrete item id를 task 생성 시점에 줄 수 있습니다. `SETUP_MACHINE`은 item을 고르거나 운반하지 않고, 이미 machine에 적재된 input을 바탕으로 setup만 수행합니다.

이 문서는 `data/tasks/*.json`에 정의된 HumanoidSim core task를 사람이 읽기 쉽게 정리한 reference입니다. JSON 파일이 원본이고, 이 문서는 검색과 검토를 위한 요약입니다.

## 요약

- Task 수: 86
- 원본 task 정의: `data/tasks/*.json`
- 통합 index: `data/task_catalog_core.json`
- Primitive template index: `data/primitive_templates.json`

### Level별 개수

<table>
  <colgroup>
    <col style="width: 72%;" />
    <col style="width: 28%;" />
  </colgroup>
  <thead>
    <tr>
      <th>Level</th>
      <th>개수</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>ATOMIC_TASK</code></td>
      <td>55</td>
    </tr>
    <tr>
      <td><code>COMPOSITE_TASK</code></td>
      <td>31</td>
    </tr>
  </tbody>
</table>

### Task Level 기준

HumanoidSim v0.1에서 task level은 실행 workflow의 구조로 구분합니다. Primitive 개수나 step 길이가 아니라, step이 어떤 수준의 call을 참조하는지가 기준입니다.

<table>
  <colgroup>
    <col style="width: 16%;" />
    <col style="width: 56%;" />
    <col style="width: 28%;" />
  </colgroup>
  <thead>
    <tr>
      <th>Level</th>
      <th>기준</th>
      <th>예시</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>PRIMITIVE_SKILL</code></td>
      <td>더 이상 하위 step을 갖지 않는 최소 실행 skill입니다.</td>
      <td><code>NAVIGATE_TO</code>, <code>GRASP</code>, <code>VERIFY_PLACEMENT</code></td>
    </tr>
    <tr>
      <td><code>ATOMIC_TASK</code></td>
      <td>하위 step이 모두 primitive skill로 구성된 실행 가능한 단일 task입니다.</td>
      <td><code>TRANSFER</code>, <code>LOAD_MACHINE</code>, <code>INSPECT_PRODUCT</code></td>
    </tr>
    <tr>
      <td><code>COMPOSITE_TASK</code></td>
      <td>최소 1개 이상의 child task call을 직접 포함하는 workflow입니다. orchestration용 primitive step을 함께 가질 수 있습니다.</td>
      <td><code>REPLENISH_MATERIAL</code> -> <code>TRANSFER</code>, <code>FETCH_FOR_OPERATOR</code> -> <code>HANDOVER_ITEM</code></td>
    </tr>
  </tbody>
</table>

`StepCall.call_code`는 primitive code뿐 아니라 task code도 참조할 수 있습니다. 이때 `expected_level`은 필수이며, nested task step에서는 `ATOMIC_TASK` 또는 `COMPOSITE_TASK`로 명시합니다.

### Category 설명

<table>
  <colgroup>
    <col style="width: 7%;" />
    <col style="width: 27%;" />
    <col style="width: 8%;" />
    <col style="width: 58%;" />
  </colgroup>
  <thead>
    <tr>
      <th>ID</th>
      <th>Category</th>
      <th>개수</th>
      <th>설명</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>A</td>
      <td>Robot Readiness &amp; Self-Operation</td>
      <td>8</td>
      <td>휴머노이드 자체 운용 준비, 모드 설정, 작업 context 로딩, 전원 관리, fault recovery를 다룹니다.</td>
    </tr>
    <tr>
      <td>B</td>
      <td>Mobility, Intralogistics &amp; Material Flow</td>
      <td>5</td>
      <td>자재, WIP, 완성품, tool을 위치 사이에서 이동하거나 물류 흐름을 조정하는 작업을 다룹니다.</td>
    </tr>
    <tr>
      <td>C</td>
      <td>Machine Tending &amp; Equipment Operation</td>
      <td>7</td>
      <td>설비 setup, load/unload, HMI 조작, cycle 제어, configuration 변경과 설비 fault 처리를 다룹니다.</td>
    </tr>
    <tr>
      <td>D</td>
      <td>Assembly, Fastening &amp; Connection</td>
      <td>9</td>
      <td>부품 조립, 분해, 체결, 삽입, 제거, 연결 같은 assembly 작업을 다룹니다.</td>
    </tr>
    <tr>
      <td>E</td>
      <td>Material Application, Dispensing &amp; Sealing</td>
      <td>5</td>
      <td>표면 준비, 도포, dispensing, sealing, 경화, 도포 상태 검증을 다룹니다.</td>
    </tr>
    <tr>
      <td>F</td>
      <td>Processing, Rework &amp; Surface Treatment</td>
      <td>5</td>
      <td>절단, trimming, feature 생성, burr 제거, 표면 마감, marking 같은 가공과 rework를 다룹니다.</td>
    </tr>
    <tr>
      <td>G</td>
      <td>Quality Inspection, Measurement &amp; Testing</td>
      <td>7</td>
      <td>품질 검사, 측정, 기능 test, item 식별, 검사 결과 기록과 분류를 다룹니다.</td>
    </tr>
    <tr>
      <td>H</td>
      <td>Maintenance, Repair &amp; Calibration</td>
      <td>7</td>
      <td>예방정비, 설비 점검, 진단, 수리, 부품 교체, 윤활, calibration을 다룹니다.</td>
    </tr>
    <tr>
      <td>I</td>
      <td>Cleaning, 5S, EHS &amp; Safety Patrol</td>
      <td>6</td>
      <td>작업 구역과 asset 청소, scrap 수거, spill 대응, EHS/5S audit, hazard report를 다룹니다.</td>
    </tr>
    <tr>
      <td>J</td>
      <td>Packaging, Unitization &amp; Shipping</td>
      <td>5</td>
      <td>제품 포장, 개봉, label, package 검증, palletizing, wrapping, shipping 준비를 다룹니다.</td>
    </tr>
    <tr>
      <td>K</td>
      <td>Warehouse, Inventory &amp; Material Control</td>
      <td>6</td>
      <td>입고, putaway, picking, 재고 count/audit, kit 구성, inventory record 갱신을 다룹니다.</td>
    </tr>
    <tr>
      <td>L</td>
      <td>MES, Traceability &amp; Digital Operations</td>
      <td>6</td>
      <td>work order, operation result, traceability, exception report, evidence/status capture 같은 digital operation을 다룹니다.</td>
    </tr>
    <tr>
      <td>M</td>
      <td>Human Collaboration &amp; Operator Assistance</td>
      <td>6</td>
      <td>operator 지원, item/tool handover, operator로부터 수령, 작업 중 지지/정렬, 공동 lifting/move를 다룹니다.</td>
    </tr>
    <tr>
      <td>S</td>
      <td>Shipyard Construction, Coating &amp; Verification</td>
      <td>4</td>
      <td>조선소 선박 section 또는 exterior surface tile의 용접, 표면처리, sealant 적용, 도장, 품질 확인 작업을 다룹니다.</td>
    </tr>
  </tbody>
</table>

## 전체 Task 목록

<table>
  <colgroup>
    <col style="width: 4%;" />
    <col style="width: 10%;" />
    <col style="width: 9%;" />
    <col style="width: 26%;" />
    <col style="width: 11%;" />
    <col style="width: 9%;" />
    <col style="width: 9%;" />
    <col style="width: 4%;" />
    <col style="width: 12%;" />
    <col style="width: 6%;" />
  </colgroup>
  <thead>
    <tr>
      <th>No</th>
      <th>Code</th>
      <th>Level</th>
      <th>설명</th>
      <th>입력</th>
      <th>Capabilities</th>
      <th>Resources</th>
      <th>Risk</th>
      <th>Step / Nested Sequence</th>
      <th>원본</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>A01</td>
      <td><code>INITIALIZE_ROBOT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>context*: Any</td>
      <td>system_operation<br>digital_context<br>equipment_interaction</td>
      <td>equipment:robot<br>equipment:charger<br>equipment:network</td>
      <td>LOW</td>
      <td><code>CHECK_CONTEXT</code><br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A01_INITIALIZE_ROBOT.json</code></td>
    </tr>
    <tr>
      <td>A02</td>
      <td><code>SELF_CHECK</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>checklist*: Any</td>
      <td>system_operation<br>digital_context<br>equipment_interaction</td>
      <td>equipment:robot_diagnostics</td>
      <td>LOW</td>
      <td><code>CHECK_CONTEXT</code><br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A02_SELF_CHECK.json</code></td>
    </tr>
    <tr>
      <td>A03</td>
      <td><code>SET_OPERATION_MODE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>mode*: Any<br>constraints*: Any</td>
      <td>system_operation<br>digital_context<br>equipment_interaction</td>
      <td>equipment:robot_controller</td>
      <td>MEDIUM</td>
      <td><code>CHECK_CONTEXT</code><br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A03_SET_OPERATION_MODE.json</code></td>
    </tr>
    <tr>
      <td>A04</td>
      <td><code>LOAD_WORK_CONTEXT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>map_id*: Any<br>work_order_id*: Any<br>skill_set*: Any</td>
      <td>system_operation<br>digital_context<br>equipment_interaction</td>
      <td>equipment:mes<br>equipment:wms<br>equipment:map_server<br>equipment:robot_controller</td>
      <td>LOW</td>
      <td><code>CHECK_CONTEXT</code><br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A04_LOAD_WORK_CONTEXT.json</code></td>
    </tr>
    <tr>
      <td>A05</td>
      <td><code>CALIBRATE_ROBOT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>calibration_target*: Any<br>calibration_type*: Any</td>
      <td>system_operation<br>digital_context<br>tool_use<br>equipment_interaction</td>
      <td>tool:calibration_artifact<br>equipment:calibration_target<br>equipment:controller</td>
      <td>MEDIUM</td>
      <td><code>CHECK_CONTEXT</code><br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A05_CALIBRATE_ROBOT.json</code></td>
    </tr>
    <tr>
      <td>A06</td>
      <td><code>CHANGE_END_EFFECTOR</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>end_effector*: Any<br>station*: LocationRef | str</td>
      <td>system_operation<br>digital_context<br>tool_use<br>equipment_interaction</td>
      <td>tool:end_effector<br>tool:tool_changer<br>equipment:tool_changer_station</td>
      <td>MEDIUM</td>
      <td><code>CHECK_CONTEXT</code><br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A06_CHANGE_END_EFFECTOR.json</code></td>
    </tr>
    <tr>
      <td>A07</td>
      <td><code>MANAGE_ROBOT_POWER</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>action*: Any<br>station*: LocationRef | str<br>target_soc*: float</td>
      <td>system_operation<br>digital_context<br>tool_use<br>equipment_interaction</td>
      <td>tool:battery_pack<br>equipment:charger<br>equipment:docking_station<br>equipment:battery_swap_station</td>
      <td>LOW</td>
      <td><code>CHECK_CONTEXT</code><br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A07_MANAGE_ROBOT_POWER.json</code></td>
    </tr>
    <tr>
      <td>A08</td>
      <td><code>RECOVER_FROM_FAULT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>휴머노이드 자체 상태를 준비, 점검, 복구하거나 운용 context를 설정하는 task입니다.</td>
      <td>robot*: EntityRef | str<br>fault_code*: Any<br>policy*: Any</td>
      <td>system_operation<br>digital_context<br>equipment_interaction</td>
      <td>equipment:robot_controller<br>equipment:logs</td>
      <td>MEDIUM</td>
      <td><code>CHECK_CONTEXT</code><br><code>SELF_CHECK</code> [ATOMIC_TASK]<br><code>EXECUTE_SYSTEM_ACTION</code><br><code>VERIFY_ROBOT_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/A08_RECOVER_FROM_FAULT.json</code></td>
    </tr>
    <tr>
      <td>B01</td>
      <td><code>TRANSFER</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>자재, WIP, 제품 또는 tool을 위치 사이에서 이동하고 물류 상태를 바꾸는 task입니다.</td>
      <td>item*: EntityRef | str<br>source*: LocationRef | str<br>destination*: LocationRef | str</td>
      <td>navigation<br>object_localization<br>manipulation<br>payload_handling<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:handling_tool<br>vehicle:cart<br>vehicle:pallet_jack<br>vehicle:forklift<br>vehicle:amr<br>vehicle:elevator<br>equipment:source<br>equipment:destination_locations</td>
      <td>LOW</td>
      <td><code>NAVIGATE_TO</code><br><code>LOCALIZE_OBJECT</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>LIFT</code><br><code>NAVIGATE_TO</code><br><code>PLACE</code><br><code>RELEASE</code><br><code>VERIFY_PLACEMENT</code></td>
      <td><code>data/tasks/B01_TRANSFER.json</code></td>
    </tr>
    <tr>
      <td>B02</td>
      <td><code>REPLENISH_MATERIAL</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>자재, WIP, 제품 또는 tool을 위치 사이에서 이동하고 물류 상태를 바꾸는 task입니다.</td>
      <td>item*: EntityRef | str<br>destination*: LocationRef | str<br>rule*: Any<br>source*: LocationRef | str</td>
      <td>navigation<br>manipulation<br>inventory_interaction<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:cart<br>vehicle:pallet_jack<br>vehicle:forklift<br>vehicle:amr<br>equipment:storage<br>equipment:line_station<br>equipment:bin</td>
      <td>LOW</td>
      <td><code>CHECK_REQUEST</code><br><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>TRANSFER</code> [ATOMIC_TASK]<br><code>VERIFY_LEVEL_OR_QUANTITY</code><br><code>UPDATE_RECORD</code></td>
      <td><code>data/tasks/B02_REPLENISH_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>B03</td>
      <td><code>REMOVE_MATERIAL</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>자재, WIP, 제품 또는 tool을 위치 사이에서 이동하고 물류 상태를 바꾸는 task입니다.</td>
      <td>item*: EntityRef | str<br>source*: LocationRef | str<br>destination*: LocationRef | str<br>reason*: Any</td>
      <td>navigation<br>manipulation<br>inventory_interaction<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:cart<br>vehicle:pallet_jack<br>vehicle:forklift<br>vehicle:amr<br>equipment:collection_area<br>equipment:quarantine<br>equipment:scrap_area</td>
      <td>LOW</td>
      <td><code>CHECK_REQUEST</code><br><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>TRANSFER</code> [ATOMIC_TASK]<br><code>VERIFY_LEVEL_OR_QUANTITY</code><br><code>UPDATE_RECORD</code></td>
      <td><code>data/tasks/B03_REMOVE_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>B04</td>
      <td><code>LOAD_UNLOAD_TRANSFER_INTERFACE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>자재, WIP, 제품 또는 tool을 위치 사이에서 이동하고 물류 상태를 바꾸는 task입니다.</td>
      <td>item*: EntityRef | str<br>interface*: Any<br>action*: Any<br>destination*: LocationRef | str</td>
      <td>navigation<br>object_localization<br>manipulation<br>payload_handling<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:vehicle<br>equipment:conveyor<br>equipment:asrs<br>equipment:dock<br>equipment:elevator<br>equipment:staging_interface</td>
      <td>MEDIUM</td>
      <td><code>NAVIGATE_TO</code><br><code>LOCALIZE_OBJECT</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>LIFT</code><br><code>NAVIGATE_TO</code><br><code>PLACE</code><br><code>RELEASE</code><br><code>VERIFY_PLACEMENT</code></td>
      <td><code>data/tasks/B04_LOAD_UNLOAD_TRANSFER_INTERFACE.json</code></td>
    </tr>
    <tr>
      <td>B05</td>
      <td><code>OPERATE_VEHICLE_TRANSPORT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>자재, WIP, 제품 또는 tool을 위치 사이에서 이동하고 물류 상태를 바꾸는 task입니다.</td>
      <td>vehicle*: Any<br>item*: EntityRef | str<br>source*: LocationRef | str<br>destination*: LocationRef | str<br>route*: Any</td>
      <td>navigation<br>vehicle_operation<br>load_handling<br>tool_use<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:scanner<br>vehicle:forklift<br>vehicle:pallet_jack<br>vehicle:tugger<br>vehicle:cart<br>vehicle:amr<br>vehicle:elevator<br>equipment:vehicle<br>equipment:route<br>equipment:parking<br>equipment:charging_area</td>
      <td>HIGH</td>
      <td><code>VERIFY_AUTHORIZATION</code><br><code>TRANSFER</code> [ATOMIC_TASK]<br><code>PARK_OR_RELEASE_VEHICLE</code><br><code>VERIFY_PLACEMENT</code></td>
      <td><code>data/tasks/B05_OPERATE_VEHICLE_TRANSPORT.json</code></td>
    </tr>
    <tr>
      <td>C01</td>
      <td><code>SETUP_MACHINE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>setup_spec*: Any</td>
      <td>machine_interface<br>safety_zone_check<br>manipulation<br>tool_use<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:scanner<br>tool:setup_tools<br>equipment:machine<br>equipment:fixture<br>equipment:hmi<br>equipment:program<br>equipment:recipe</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>NAVIGATE_TO</code><br><code>READ_MACHINE_STATE</code><br><code>EXECUTE_MACHINE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/C01_SETUP_MACHINE.json</code></td>
    </tr>
    <tr>
      <td>C02</td>
      <td><code>LOAD_MACHINE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>item*: EntityRef | str<br>source*: LocationRef | str<br>target_slot*: Any</td>
      <td>machine_interface<br>safety_zone_check<br>manipulation<br>tool_use<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:gripper<br>tool:tool<br>equipment:machine<br>equipment:fixture<br>equipment:guard<br>equipment:door</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>NAVIGATE_TO</code><br><code>READ_MACHINE_STATE</code><br><code>EXECUTE_MACHINE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/C02_LOAD_MACHINE.json</code></td>
    </tr>
    <tr>
      <td>C03</td>
      <td><code>UNLOAD_MACHINE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>item*: EntityRef | str<br>destination*: LocationRef | str</td>
      <td>machine_interface<br>safety_zone_check<br>manipulation<br>tool_use<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:gripper<br>tool:tool<br>equipment:machine<br>equipment:fixture<br>equipment:guard<br>equipment:door</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>NAVIGATE_TO</code><br><code>READ_MACHINE_STATE</code><br><code>EXECUTE_MACHINE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/C03_UNLOAD_MACHINE.json</code></td>
    </tr>
    <tr>
      <td>C04</td>
      <td><code>OPERATE_MACHINE_INTERFACE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>interface_action*: Any</td>
      <td>machine_interface<br>safety_zone_check<br>manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>equipment:hmi<br>equipment:panel<br>equipment:buttons<br>equipment:levers<br>equipment:display</td>
      <td>MEDIUM</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>NAVIGATE_TO</code><br><code>READ_MACHINE_STATE</code><br><code>EXECUTE_MACHINE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/C04_OPERATE_MACHINE_INTERFACE.json</code></td>
    </tr>
    <tr>
      <td>C05</td>
      <td><code>CONTROL_MACHINE_CYCLE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>action*: Any<br>program_id*: Any</td>
      <td>machine_interface<br>safety_zone_check<br>manipulation<br>equipment_interaction<br>high_risk_task</td>
      <td>equipment:machine_controller<br>equipment:hmi</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>NAVIGATE_TO</code><br><code>READ_MACHINE_STATE</code><br><code>EXECUTE_MACHINE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/C05_CONTROL_MACHINE_CYCLE.json</code></td>
    </tr>
    <tr>
      <td>C06</td>
      <td><code>CHANGE_MACHINE_CONFIGURATION</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>from_config*: Any<br>to_config*: Any</td>
      <td>machine_interface<br>safety_zone_check<br>manipulation<br>tool_use<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:setup_tools<br>equipment:machine<br>equipment:tools<br>equipment:fixture<br>equipment:jig<br>equipment:recipe<br>equipment:program</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>OPERATE_MACHINE_INTERFACE</code> [ATOMIC_TASK]<br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/C06_CHANGE_MACHINE_CONFIGURATION.json</code></td>
    </tr>
    <tr>
      <td>C07</td>
      <td><code>CLEAR_MACHINE_FAULT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비를 준비, 조작, 적재, 하역, 복구하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>fault*: Any<br>procedure*: Any</td>
      <td>machine_interface<br>safety_zone_check<br>manipulation<br>tool_use<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:maintenance_tools<br>equipment:machine<br>equipment:alarm_panel<br>equipment:jam_location</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>OPERATE_MACHINE_INTERFACE</code> [ATOMIC_TASK]<br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/C07_CLEAR_MACHINE_FAULT.json</code></td>
    </tr>
    <tr>
      <td>D01</td>
      <td><code>ASSEMBLE_COMPONENTS</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>components*: Any<br>target_assembly*: Any<br>sequence*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:assembly_tools<br>equipment:fixture<br>equipment:assembly_station</td>
      <td>MEDIUM</td>
      <td><code>INSERT_COMPONENT</code> [ATOMIC_TASK]<br><code>FASTEN_COMPONENT</code> [ATOMIC_TASK]<br><code>VERIFY_ASSEMBLY</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/D01_ASSEMBLE_COMPONENTS.json</code></td>
    </tr>
    <tr>
      <td>D02</td>
      <td><code>DISASSEMBLE_COMPONENTS</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>assembly*: Any<br>components*: Any<br>sequence*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:assembly_tools<br>equipment:fixture<br>equipment:assembly_station</td>
      <td>MEDIUM</td>
      <td><code>UNFASTEN_COMPONENT</code> [ATOMIC_TASK]<br><code>REMOVE_COMPONENT</code> [ATOMIC_TASK]<br><code>VERIFY_ASSEMBLY</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/D02_DISASSEMBLE_COMPONENTS.json</code></td>
    </tr>
    <tr>
      <td>D03</td>
      <td><code>INSERT_COMPONENT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>component*: Any<br>target*: Any<br>insertion_spec*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:insertion_tool<br>equipment:fixture<br>equipment:target_feature</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_COMPONENTS</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>ALIGN</code><br><code>EXECUTE_ASSEMBLY_ACTION</code><br><code>RELEASE</code><br><code>PRIMITIVE_VERIFY_ASSEMBLY</code></td>
      <td><code>data/tasks/D03_INSERT_COMPONENT.json</code></td>
    </tr>
    <tr>
      <td>D04</td>
      <td><code>REMOVE_COMPONENT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>component*: Any<br>source*: LocationRef | str<br>removal_spec*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:removal<br>tool:pry_tool<br>equipment:fixture<br>equipment:assembly</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_COMPONENTS</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>ALIGN</code><br><code>EXECUTE_ASSEMBLY_ACTION</code><br><code>RELEASE</code><br><code>PRIMITIVE_VERIFY_ASSEMBLY</code></td>
      <td><code>data/tasks/D04_REMOVE_COMPONENT.json</code></td>
    </tr>
    <tr>
      <td>D05</td>
      <td><code>FASTEN_COMPONENT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>fastener*: Any<br>target*: Any<br>fastening_spec*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:torque_driver<br>tool:nutrunner<br>tool:rivet_tool<br>equipment:fixture<br>equipment:assembly</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_COMPONENTS</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>ALIGN</code><br><code>EXECUTE_ASSEMBLY_ACTION</code><br><code>RELEASE</code><br><code>PRIMITIVE_VERIFY_ASSEMBLY</code></td>
      <td><code>data/tasks/D05_FASTEN_COMPONENT.json</code></td>
    </tr>
    <tr>
      <td>D06</td>
      <td><code>UNFASTEN_COMPONENT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>fastener*: Any<br>target*: Any<br>unfastening_spec*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:torque_driver<br>tool:nutrunner<br>tool:removal_tool<br>equipment:fixture<br>equipment:assembly</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_COMPONENTS</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>ALIGN</code><br><code>EXECUTE_ASSEMBLY_ACTION</code><br><code>RELEASE</code><br><code>PRIMITIVE_VERIFY_ASSEMBLY</code></td>
      <td><code>data/tasks/D06_UNFASTEN_COMPONENT.json</code></td>
    </tr>
    <tr>
      <td>D07</td>
      <td><code>CONNECT_COMPONENT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>component_a*: Any<br>component_b*: Any<br>connection_spec*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:crimp<br>tool:connector_tool<br>equipment:assembly<br>equipment:port<br>equipment:connector<br>equipment:harness</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_COMPONENTS</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>ALIGN</code><br><code>EXECUTE_ASSEMBLY_ACTION</code><br><code>RELEASE</code><br><code>PRIMITIVE_VERIFY_ASSEMBLY</code></td>
      <td><code>data/tasks/D07_CONNECT_COMPONENT.json</code></td>
    </tr>
    <tr>
      <td>D08</td>
      <td><code>DISCONNECT_COMPONENT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>component_a*: Any<br>component_b*: Any<br>disconnection_spec*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:removal_tool<br>equipment:assembly<br>equipment:port<br>equipment:connector<br>equipment:harness</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_COMPONENTS</code><br><code>REACH_TO</code><br><code>GRASP</code><br><code>ALIGN</code><br><code>EXECUTE_ASSEMBLY_ACTION</code><br><code>RELEASE</code><br><code>PRIMITIVE_VERIFY_ASSEMBLY</code></td>
      <td><code>data/tasks/D08_DISCONNECT_COMPONENT.json</code></td>
    </tr>
    <tr>
      <td>D09</td>
      <td><code>ROUTE_FLEXIBLE_COMPONENT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>부품을 조립, 분해, 삽입, 제거, 체결, 연결하는 task입니다.</td>
      <td>component*: Any<br>path*: LocationRef | str<br>securing_spec*: Any</td>
      <td>assembly_manipulation<br>object_localization<br>fine_manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:clip<br>tool:tie<br>tool:tape_tool<br>equipment:clips<br>equipment:guides<br>equipment:assembly</td>
      <td>MEDIUM</td>
      <td><code>INSERT_COMPONENT</code> [ATOMIC_TASK]<br><code>CONNECT_COMPONENT</code> [ATOMIC_TASK]<br><code>VERIFY_ASSEMBLY</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/D09_ROUTE_FLEXIBLE_COMPONENT.json</code></td>
    </tr>
    <tr>
      <td>E01</td>
      <td><code>PREPARE_SURFACE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>표면이나 대상물에 소재를 적용하거나 적용 상태를 검증하는 task입니다.</td>
      <td>surface*: Any<br>preparation_spec*: Any</td>
      <td>material_application<br>surface_preparation<br>tool_use<br>equipment_interaction</td>
      <td>tool:wiper<br>tool:solvent<br>tool:masking_tool<br>equipment:surface<br>equipment:fixture<br>equipment:cleaning_supplies</td>
      <td>LOW</td>
      <td><code>LOCALIZE_SURFACE</code><br><code>PRIMITIVE_PREPARE_SURFACE</code><br><code>OPERATE_TOOL_OR_DISPENSER</code><br><code>PRIMITIVE_APPLY_MATERIAL</code><br><code>VERIFY_COVERAGE_OR_AMOUNT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/E01_PREPARE_SURFACE.json</code></td>
    </tr>
    <tr>
      <td>E02</td>
      <td><code>APPLY_MATERIAL</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>표면이나 대상물에 소재를 적용하거나 적용 상태를 검증하는 task입니다.</td>
      <td>material*: Any<br>target*: Any<br>application_spec*: Any</td>
      <td>material_application<br>surface_preparation<br>tool_use<br>equipment_interaction</td>
      <td>tool:dispenser<br>tool:sprayer<br>tool:grease_gun<br>tool:tape_tool<br>equipment:material_container<br>equipment:target_surface</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_SURFACE</code><br><code>PRIMITIVE_PREPARE_SURFACE</code><br><code>OPERATE_TOOL_OR_DISPENSER</code><br><code>PRIMITIVE_APPLY_MATERIAL</code><br><code>VERIFY_COVERAGE_OR_AMOUNT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/E02_APPLY_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>E03</td>
      <td><code>REMOVE_APPLIED_MATERIAL</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>표면이나 대상물에 소재를 적용하거나 적용 상태를 검증하는 task입니다.</td>
      <td>material_or_residue*: Any<br>target*: Any<br>removal_spec*: Any</td>
      <td>material_application<br>surface_preparation<br>tool_use<br>equipment_interaction</td>
      <td>tool:scraper<br>tool:wiper<br>tool:solvent<br>equipment:target_surface<br>equipment:waste_container</td>
      <td>LOW</td>
      <td><code>LOCALIZE_SURFACE</code><br><code>PRIMITIVE_PREPARE_SURFACE</code><br><code>OPERATE_TOOL_OR_DISPENSER</code><br><code>PRIMITIVE_APPLY_MATERIAL</code><br><code>VERIFY_COVERAGE_OR_AMOUNT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/E03_REMOVE_APPLIED_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>E04</td>
      <td><code>CURE_MATERIAL</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>표면이나 대상물에 소재를 적용하거나 적용 상태를 검증하는 task입니다.</td>
      <td>material*: Any<br>target*: Any<br>cure_profile*: Any</td>
      <td>material_application<br>surface_preparation<br>tool_use<br>equipment_interaction</td>
      <td>tool:uv<br>tool:heat_tool<br>equipment:oven<br>equipment:uv_lamp<br>equipment:curing_fixture</td>
      <td>MEDIUM</td>
      <td><code>PREPARE_SURFACE</code> [ATOMIC_TASK]<br><code>APPLY_MATERIAL</code> [ATOMIC_TASK]<br><code>VERIFY_MATERIAL_APPLICATION</code> [ATOMIC_TASK]<br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/E04_CURE_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>E05</td>
      <td><code>VERIFY_MATERIAL_APPLICATION</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>표면이나 대상물에 소재를 적용하거나 적용 상태를 검증하는 task입니다.</td>
      <td>target*: Any<br>verification_spec*: Any</td>
      <td>material_application<br>surface_preparation<br>tool_use<br>equipment_interaction</td>
      <td>tool:camera<br>tool:scale<br>tool:gauge<br>equipment:inspection_camera<br>equipment:target</td>
      <td>LOW</td>
      <td><code>LOCALIZE_SURFACE</code><br><code>PRIMITIVE_PREPARE_SURFACE</code><br><code>OPERATE_TOOL_OR_DISPENSER</code><br><code>PRIMITIVE_APPLY_MATERIAL</code><br><code>VERIFY_COVERAGE_OR_AMOUNT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/E05_VERIFY_MATERIAL_APPLICATION.json</code></td>
    </tr>
    <tr>
      <td>F01</td>
      <td><code>CUT_OR_TRIM_MATERIAL</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품의 형상, 표면, marker를 가공하거나 rework하는 task입니다.</td>
      <td>target*: Any<br>path_or_feature*: LocationRef | str<br>process_spec*: Any</td>
      <td>tool_use<br>process_rework<br>inspection<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:cutter<br>tool:knife<br>tool:shear<br>tool:laser_assist<br>equipment:workholding_fixture</td>
      <td>HIGH</td>
      <td><code>LOCALIZE_PART</code><br><code>FIX_OR_HOLD_PART</code><br><code>OPERATE_TOOL</code><br><code>PROCESS_FEATURE_OR_SURFACE</code><br><code>INSPECT_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/F01_CUT_OR_TRIM_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>F02</td>
      <td><code>CREATE_FEATURE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품의 형상, 표면, marker를 가공하거나 rework하는 task입니다.</td>
      <td>target*: Any<br>feature_spec*: Any<br>process_spec*: Any</td>
      <td>tool_use<br>process_rework<br>inspection<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:drill<br>tool:tap<br>tool:reamer<br>tool:tool<br>equipment:fixture<br>equipment:part</td>
      <td>HIGH</td>
      <td><code>LOCALIZE_PART</code><br><code>FIX_OR_HOLD_PART</code><br><code>OPERATE_TOOL</code><br><code>PROCESS_FEATURE_OR_SURFACE</code><br><code>INSPECT_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/F02_CREATE_FEATURE.json</code></td>
    </tr>
    <tr>
      <td>F03</td>
      <td><code>REMOVE_BURR_OR_FLASH</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품의 형상, 표면, marker를 가공하거나 rework하는 task입니다.</td>
      <td>part*: EntityRef | str<br>area*: LocationRef | str<br>process_spec*: Any</td>
      <td>tool_use<br>process_rework<br>inspection<br>equipment_interaction</td>
      <td>tool:deburring_tool<br>tool:file<br>tool:scraper<br>equipment:part<br>equipment:fixture</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_PART</code><br><code>FIX_OR_HOLD_PART</code><br><code>OPERATE_TOOL</code><br><code>PROCESS_FEATURE_OR_SURFACE</code><br><code>INSPECT_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/F03_REMOVE_BURR_OR_FLASH.json</code></td>
    </tr>
    <tr>
      <td>F04</td>
      <td><code>FINISH_SURFACE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품의 형상, 표면, marker를 가공하거나 rework하는 task입니다.</td>
      <td>surface*: Any<br>finish_spec*: Any</td>
      <td>tool_use<br>process_rework<br>inspection<br>equipment_interaction</td>
      <td>tool:grinder<br>tool:sander<br>tool:polisher<br>equipment:surface<br>equipment:fixture</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_PART</code><br><code>FIX_OR_HOLD_PART</code><br><code>OPERATE_TOOL</code><br><code>PROCESS_FEATURE_OR_SURFACE</code><br><code>INSPECT_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/F04_FINISH_SURFACE.json</code></td>
    </tr>
    <tr>
      <td>F05</td>
      <td><code>MARK_PART</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>부품의 형상, 표면, marker를 가공하거나 rework하는 task입니다.</td>
      <td>part*: EntityRef | str<br>mark_spec*: Any</td>
      <td>tool_use<br>process_rework<br>inspection<br>equipment_interaction</td>
      <td>tool:marker<br>tool:engraver<br>tool:printer<br>equipment:part<br>equipment:marking_station</td>
      <td>LOW</td>
      <td><code>LOCALIZE_PART</code><br><code>FIX_OR_HOLD_PART</code><br><code>OPERATE_TOOL</code><br><code>PROCESS_FEATURE_OR_SURFACE</code><br><code>INSPECT_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/F05_MARK_PART.json</code></td>
    </tr>
    <tr>
      <td>G01</td>
      <td><code>INSPECT_PRODUCT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.</td>
      <td>target*: Any<br>inspection_plan*: Any</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:camera<br>tool:light<br>tool:gauge<br>equipment:inspection_station<br>equipment:target</td>
      <td>LOW</td>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>LOCALIZE_OBJECT</code><br><code>EXECUTE_QUALITY_ACTION</code><br><code>CLASSIFY_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/G01_INSPECT_PRODUCT.json</code></td>
    </tr>
    <tr>
      <td>G02</td>
      <td><code>MEASURE_FEATURE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.</td>
      <td>target*: Any<br>feature*: Any<br>measurement_spec*: Any</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:gauge<br>tool:scale<br>tool:torque_tool<br>tool:sensor<br>equipment:measurement_tool<br>equipment:target</td>
      <td>LOW</td>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>LOCALIZE_OBJECT</code><br><code>EXECUTE_QUALITY_ACTION</code><br><code>CLASSIFY_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/G02_MEASURE_FEATURE.json</code></td>
    </tr>
    <tr>
      <td>G03</td>
      <td><code>IDENTIFY_ITEM</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.</td>
      <td>target*: Any<br>id_spec*: Any</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>tool:rfid_reader<br>tool:camera<br>equipment:label<br>equipment:tag<br>equipment:code<br>equipment:mes<br>equipment:wms</td>
      <td>LOW</td>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>LOCALIZE_OBJECT</code><br><code>EXECUTE_QUALITY_ACTION</code><br><code>CLASSIFY_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/G03_IDENTIFY_ITEM.json</code></td>
    </tr>
    <tr>
      <td>G04</td>
      <td><code>VERIFY_ASSEMBLY</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.</td>
      <td>assembly*: Any<br>verification_plan*: Any</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:camera<br>tool:gauge<br>tool:scanner<br>equipment:assembly<br>equipment:fixture</td>
      <td>LOW</td>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>LOCALIZE_OBJECT</code><br><code>EXECUTE_QUALITY_ACTION</code><br><code>CLASSIFY_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/G04_VERIFY_ASSEMBLY.json</code></td>
    </tr>
    <tr>
      <td>G05</td>
      <td><code>RUN_TEST</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.</td>
      <td>target*: Any<br>tester*: Any<br>test_plan*: Any</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:test_leads<br>tool:fixtures<br>equipment:tester<br>equipment:fixture<br>equipment:target</td>
      <td>MEDIUM</td>
      <td><code>IDENTIFY_ITEM</code> [ATOMIC_TASK]<br><code>INSPECT_PRODUCT</code> [ATOMIC_TASK]<br><code>RECORD_QUALITY_RESULT</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/G05_RUN_TEST.json</code></td>
    </tr>
    <tr>
      <td>G06</td>
      <td><code>RECORD_QUALITY_RESULT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.</td>
      <td>target*: Any<br>result*: Any<br>evidence*: Any</td>
      <td>digital_transaction<br>traceability<br>equipment_interaction</td>
      <td>equipment:mes<br>equipment:qms<br>equipment:database</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/G06_RECORD_QUALITY_RESULT.json</code></td>
    </tr>
    <tr>
      <td>G07</td>
      <td><code>SORT_OR_QUARANTINE_ITEM</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>품질 검사, 측정, test, 식별, 결과 기록과 분류를 수행하는 task입니다.</td>
      <td>item*: EntityRef | str<br>result*: Any<br>destinations*: LocationRef | str</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>tool:labeler<br>vehicle:cart<br>vehicle:amr<br>equipment:pass<br>equipment:fail<br>equipment:quarantine_locations</td>
      <td>LOW</td>
      <td><code>IDENTIFY_ITEM</code> [ATOMIC_TASK]<br><code>INSPECT_PRODUCT</code> [ATOMIC_TASK]<br><code>RECORD_QUALITY_RESULT</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/G07_SORT_OR_QUARANTINE_ITEM.json</code></td>
    </tr>
    <tr>
      <td>H01</td>
      <td><code>PREVENTIVE_MAINTENANCE</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.</td>
      <td>asset*: EntityRef | str<br>checklist*: Any</td>
      <td>maintenance<br>diagnostics<br>tool_use<br>safety_zone_check<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:maintenance_tools<br>equipment:machine<br>equipment:spare_parts<br>equipment:checklist</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>INSPECT_MACHINE</code> [ATOMIC_TASK]<br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/H01_PREVENTIVE_MAINTENANCE.json</code></td>
    </tr>
    <tr>
      <td>H02</td>
      <td><code>INSPECT_MACHINE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>inspection_plan*: Any</td>
      <td>maintenance<br>diagnostics<br>tool_use<br>safety_zone_check<br>equipment_interaction</td>
      <td>tool:camera<br>tool:gauge<br>tool:sensor<br>equipment:machine<br>equipment:guards<br>equipment:indicators</td>
      <td>MEDIUM</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>VERIFY_LOCKOUT_IF_REQUIRED</code><br><code>INSPECT_OR_DIAGNOSE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/H02_INSPECT_MACHINE.json</code></td>
    </tr>
    <tr>
      <td>H03</td>
      <td><code>DIAGNOSE_MACHINE</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>symptoms*: Any<br>diagnostic_plan*: Any</td>
      <td>maintenance<br>diagnostics<br>tool_use<br>safety_zone_check<br>equipment_interaction</td>
      <td>tool:diagnostic_tools<br>equipment:machine<br>equipment:logs<br>equipment:hmi</td>
      <td>MEDIUM</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>INSPECT_MACHINE</code> [ATOMIC_TASK]<br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/H03_DIAGNOSE_MACHINE.json</code></td>
    </tr>
    <tr>
      <td>H04</td>
      <td><code>REPAIR_MACHINE</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>fault*: Any<br>repair_procedure*: Any</td>
      <td>maintenance<br>diagnostics<br>tool_use<br>safety_zone_check<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:maintenance_tools<br>equipment:machine<br>equipment:spare_parts</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>INSPECT_MACHINE</code> [ATOMIC_TASK]<br><code>EXECUTE_MAINTENANCE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/H04_REPAIR_MACHINE.json</code></td>
    </tr>
    <tr>
      <td>H05</td>
      <td><code>REPLACE_MACHINE_PART</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>part*: EntityRef | str<br>replacement_spec*: Any</td>
      <td>maintenance<br>diagnostics<br>tool_use<br>safety_zone_check<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:maintenance_tools<br>equipment:machine<br>equipment:spare_part</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>INSPECT_MACHINE</code> [ATOMIC_TASK]<br><code>EXECUTE_MAINTENANCE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/H05_REPLACE_MACHINE_PART.json</code></td>
    </tr>
    <tr>
      <td>H06</td>
      <td><code>SERVICE_FLUID_OR_LUBRICATION</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.</td>
      <td>asset*: EntityRef | str<br>fluid_or_lube*: Any<br>service_spec*: Any</td>
      <td>maintenance<br>diagnostics<br>tool_use<br>safety_zone_check<br>equipment_interaction</td>
      <td>tool:grease_gun<br>tool:pump<br>tool:container<br>equipment:fluid_reservoir<br>equipment:lubrication_point</td>
      <td>MEDIUM</td>
      <td><code>INSPECT_MACHINE</code> [ATOMIC_TASK]<br><code>EXECUTE_MAINTENANCE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/H06_SERVICE_FLUID_OR_LUBRICATION.json</code></td>
    </tr>
    <tr>
      <td>H07</td>
      <td><code>CALIBRATE_MACHINE</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>설비와 asset의 정비, 진단, 수리, 교체, calibration을 수행하는 task입니다.</td>
      <td>machine*: EntityRef | str<br>calibration_plan*: Any</td>
      <td>maintenance<br>diagnostics<br>tool_use<br>safety_zone_check<br>equipment_interaction</td>
      <td>tool:calibration_tools<br>equipment:machine<br>equipment:calibration_artifact</td>
      <td>MEDIUM</td>
      <td><code>INSPECT_MACHINE</code> [ATOMIC_TASK]<br><code>EXECUTE_MAINTENANCE_ACTION</code><br><code>VERIFY_MACHINE_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/H07_CALIBRATE_MACHINE.json</code></td>
    </tr>
    <tr>
      <td>I01</td>
      <td><code>CLEAN_AREA</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>청소, scrap/waste 수거, EHS, 5S, hazard 대응을 수행하는 task입니다.</td>
      <td>area*: LocationRef | str<br>cleaning_spec*: Any</td>
      <td>cleaning<br>ehs_audit<br>hazard_reporting<br>tool_use<br>equipment_interaction</td>
      <td>tool:wiper<br>tool:vacuum<br>tool:mop<br>equipment:area<br>equipment:cleaning_supplies</td>
      <td>LOW</td>
      <td><code>CLEAN_ASSET</code> [ATOMIC_TASK]<br><code>VERIFY_AREA_STATE</code><br><code>REPORT_RESULT</code></td>
      <td><code>data/tasks/I01_CLEAN_AREA.json</code></td>
    </tr>
    <tr>
      <td>I02</td>
      <td><code>CLEAN_ASSET</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>청소, scrap/waste 수거, EHS, 5S, hazard 대응을 수행하는 task입니다.</td>
      <td>asset*: EntityRef | str<br>cleaning_spec*: Any</td>
      <td>cleaning<br>ehs_audit<br>hazard_reporting<br>tool_use<br>equipment_interaction</td>
      <td>tool:wiper<br>tool:brush<br>tool:air_nozzle<br>tool:vacuum<br>equipment:asset<br>equipment:cleaning_supplies</td>
      <td>MEDIUM</td>
      <td><code>NAVIGATE_TO</code><br><code>INSPECT_AREA</code><br><code>EXECUTE_EHS_ACTION</code><br><code>VERIFY_AREA_STATE</code><br><code>REPORT_RESULT</code></td>
      <td><code>data/tasks/I02_CLEAN_ASSET.json</code></td>
    </tr>
    <tr>
      <td>I03</td>
      <td><code>COLLECT_WASTE_OR_SCRAP</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>청소, scrap/waste 수거, EHS, 5S, hazard 대응을 수행하는 task입니다.</td>
      <td>items*: EntityRef | str<br>source*: LocationRef | str<br>destination*: LocationRef | str<br>sorting_rule*: Any</td>
      <td>cleaning<br>ehs_audit<br>hazard_reporting<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:cart<br>vehicle:amr<br>equipment:waste_bins<br>equipment:scrap_area</td>
      <td>LOW</td>
      <td><code>TRANSFER</code> [ATOMIC_TASK]<br><code>UPDATE_INVENTORY_RECORD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/I03_COLLECT_WASTE_OR_SCRAP.json</code></td>
    </tr>
    <tr>
      <td>I04</td>
      <td><code>RESPOND_TO_SPILL</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>청소, scrap/waste 수거, EHS, 5S, hazard 대응을 수행하는 task입니다.</td>
      <td>area*: LocationRef | str<br>spill_type*: Any<br>response_plan*: Any</td>
      <td>cleaning<br>ehs_audit<br>hazard_reporting<br>tool_use<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:spill_kit<br>equipment:spill_kit<br>equipment:signs<br>equipment:ehs_record</td>
      <td>HIGH</td>
      <td><code>CLEAN_AREA</code> [COMPOSITE_TASK]<br><code>REPORT_HAZARD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/I04_RESPOND_TO_SPILL.json</code></td>
    </tr>
    <tr>
      <td>I05</td>
      <td><code>CONDUCT_EHS_OR_5S_AUDIT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>청소, scrap/waste 수거, EHS, 5S, hazard 대응을 수행하는 task입니다.</td>
      <td>area*: LocationRef | str<br>checklist*: Any</td>
      <td>cleaning<br>ehs_audit<br>hazard_reporting<br>tool_use<br>equipment_interaction</td>
      <td>tool:camera<br>tool:scanner<br>equipment:area<br>equipment:checklist<br>equipment:ehs_system</td>
      <td>LOW</td>
      <td><code>CLEAN_ASSET</code> [ATOMIC_TASK]<br><code>REPORT_HAZARD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/I05_CONDUCT_EHS_OR_5S_AUDIT.json</code></td>
    </tr>
    <tr>
      <td>I06</td>
      <td><code>REPORT_HAZARD</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>청소, scrap/waste 수거, EHS, 5S, hazard 대응을 수행하는 task입니다.</td>
      <td>location*: LocationRef | str<br>hazard_type*: Any<br>evidence*: Any</td>
      <td>digital_transaction<br>traceability<br>tool_use<br>equipment_interaction</td>
      <td>tool:camera<br>equipment:ehs_system<br>equipment:supervisor_notification</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/I06_REPORT_HAZARD.json</code></td>
    </tr>
    <tr>
      <td>J01</td>
      <td><code>PACK_PRODUCT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>포장, label, unitization, shipping 준비를 수행하는 task입니다.</td>
      <td>product*: EntityRef | str<br>packaging_spec*: Any</td>
      <td>packaging<br>labeling<br>manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:tape<br>tool:glue<br>tool:packing_tool<br>equipment:packaging_material<br>equipment:box<br>equipment:tray</td>
      <td>LOW</td>
      <td><code>LABEL_ITEM_OR_PACKAGE</code> [ATOMIC_TASK]<br><code>VERIFY_PACKAGE</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/J01_PACK_PRODUCT.json</code></td>
    </tr>
    <tr>
      <td>J02</td>
      <td><code>UNPACK_MATERIAL</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>포장, label, unitization, shipping 준비를 수행하는 task입니다.</td>
      <td>package*: Any<br>destination*: LocationRef | str<br>unpack_spec*: Any</td>
      <td>packaging<br>labeling<br>manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:cutter<br>equipment:package<br>equipment:destination</td>
      <td>LOW</td>
      <td><code>VERIFY_PACKAGE</code> [ATOMIC_TASK]<br><code>UPDATE_INVENTORY_RECORD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/J02_UNPACK_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>J03</td>
      <td><code>LABEL_ITEM_OR_PACKAGE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>포장, label, unitization, shipping 준비를 수행하는 task입니다.</td>
      <td>target*: Any<br>label_spec*: Any</td>
      <td>packaging<br>labeling<br>manipulation<br>tool_use<br>equipment_interaction</td>
      <td>tool:printer<br>tool:labeler<br>tool:scanner<br>equipment:label_printer<br>equipment:target</td>
      <td>LOW</td>
      <td><code>IDENTIFY_PRODUCT</code><br><code>PREPARE_PACKAGING</code><br><code>EXECUTE_PACKAGING_ACTION</code><br><code>PRIMITIVE_VERIFY_PACKAGE</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/J03_LABEL_ITEM_OR_PACKAGE.json</code></td>
    </tr>
    <tr>
      <td>J04</td>
      <td><code>VERIFY_PACKAGE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>포장, label, unitization, shipping 준비를 수행하는 task입니다.</td>
      <td>package*: Any<br>verification_plan*: Any</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>tool:scale<br>tool:camera<br>equipment:package<br>equipment:scale<br>equipment:label</td>
      <td>LOW</td>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>LOCALIZE_OBJECT</code><br><code>EXECUTE_QUALITY_ACTION</code><br><code>CLASSIFY_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/J04_VERIFY_PACKAGE.json</code></td>
    </tr>
    <tr>
      <td>J05</td>
      <td><code>UNITIZE_LOAD</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>포장, label, unitization, shipping 준비를 수행하는 task입니다.</td>
      <td>items*: EntityRef | str<br>unitization_spec*: Any</td>
      <td>packaging<br>labeling<br>manipulation<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:wrapper<br>tool:strapper<br>vehicle:pallet_jack<br>vehicle:forklift<br>equipment:pallet<br>equipment:wrap<br>equipment:strapper<br>equipment:staging_area</td>
      <td>MEDIUM</td>
      <td><code>PACK_PRODUCT</code> [COMPOSITE_TASK]<br><code>VERIFY_PACKAGE</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/J05_UNITIZE_LOAD.json</code></td>
    </tr>
    <tr>
      <td>K01</td>
      <td><code>RECEIVE_MATERIAL</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>창고, 재고, picking, putaway, kit 구성, inventory record 갱신을 수행하는 task입니다.</td>
      <td>shipment*: Any<br>dock*: LocationRef | str<br>receiving_plan*: Any</td>
      <td>warehouse_operation<br>inventory_interaction<br>digital_recording<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:forklift<br>vehicle:pallet_jack<br>equipment:dock<br>equipment:wms<br>equipment:erp<br>equipment:receiving_area</td>
      <td>MEDIUM</td>
      <td><code>IDENTIFY_ITEM</code> [ATOMIC_TASK]<br><code>UPDATE_INVENTORY_RECORD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/K01_RECEIVE_MATERIAL.json</code></td>
    </tr>
    <tr>
      <td>K02</td>
      <td><code>PUTAWAY_ITEM</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>창고, 재고, picking, putaway, kit 구성, inventory record 갱신을 수행하는 task입니다.</td>
      <td>item*: EntityRef | str<br>storage_location*: LocationRef | str<br>putaway_rule*: Any</td>
      <td>warehouse_operation<br>inventory_interaction<br>digital_recording<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:cart<br>vehicle:forklift<br>vehicle:amr<br>equipment:storage_location<br>equipment:wms</td>
      <td>LOW</td>
      <td><code>TRANSFER</code> [ATOMIC_TASK]<br><code>UPDATE_INVENTORY_RECORD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/K02_PUTAWAY_ITEM.json</code></td>
    </tr>
    <tr>
      <td>K03</td>
      <td><code>PICK_INVENTORY</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>창고, 재고, picking, putaway, kit 구성, inventory record 갱신을 수행하는 task입니다.</td>
      <td>request*: Any<br>picking_rule*: Any</td>
      <td>warehouse_operation<br>inventory_interaction<br>digital_recording<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:cart<br>vehicle:amr<br>equipment:storage<br>equipment:wms</td>
      <td>LOW</td>
      <td><code>COUNT_INVENTORY</code> [ATOMIC_TASK]<br><code>TRANSFER</code> [ATOMIC_TASK]<br><code>UPDATE_INVENTORY_RECORD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/K03_PICK_INVENTORY.json</code></td>
    </tr>
    <tr>
      <td>K04</td>
      <td><code>COUNT_INVENTORY</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>창고, 재고, picking, putaway, kit 구성, inventory record 갱신을 수행하는 task입니다.</td>
      <td>location*: LocationRef | str<br>item_spec*: EntityRef | str<br>count_plan*: Any</td>
      <td>warehouse_operation<br>inventory_interaction<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>tool:rfid<br>tool:camera<br>equipment:storage_location<br>equipment:wms</td>
      <td>LOW</td>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>VERIFY_RECORD</code><br><code>EXECUTE_WAREHOUSE_ACTION</code><br><code>PRIMITIVE_UPDATE_INVENTORY_RECORD</code><br><code>VERIFY_RECORD</code></td>
      <td><code>data/tasks/K04_COUNT_INVENTORY.json</code></td>
    </tr>
    <tr>
      <td>K05</td>
      <td><code>BUILD_KIT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>창고, 재고, picking, putaway, kit 구성, inventory record 갱신을 수행하는 task입니다.</td>
      <td>kit_spec*: Any<br>destination*: LocationRef | str</td>
      <td>warehouse_operation<br>inventory_interaction<br>digital_recording<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:cart<br>vehicle:amr<br>equipment:kit_container<br>equipment:bom<br>equipment:wms<br>equipment:mes</td>
      <td>LOW</td>
      <td><code>PICK_INVENTORY</code> [COMPOSITE_TASK]<br><code>UPDATE_INVENTORY_RECORD</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/K05_BUILD_KIT.json</code></td>
    </tr>
    <tr>
      <td>K06</td>
      <td><code>UPDATE_INVENTORY_RECORD</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>창고, 재고, picking, putaway, kit 구성, inventory record 갱신을 수행하는 task입니다.</td>
      <td>item*: EntityRef | str<br>transaction*: Any</td>
      <td>digital_transaction<br>traceability<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>equipment:wms<br>equipment:erp</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/K06_UPDATE_INVENTORY_RECORD.json</code></td>
    </tr>
    <tr>
      <td>L01</td>
      <td><code>START_WORK_ORDER</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>MES, WMS, traceability, work order, evidence 기록을 수행하는 digital task입니다.</td>
      <td>work_order*: Any<br>station*: LocationRef | str</td>
      <td>digital_transaction<br>traceability<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>equipment:mes</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/L01_START_WORK_ORDER.json</code></td>
    </tr>
    <tr>
      <td>L02</td>
      <td><code>COMPLETE_WORK_ORDER</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>MES, WMS, traceability, work order, evidence 기록을 수행하는 digital task입니다.</td>
      <td>work_order*: Any<br>result*: Any</td>
      <td>digital_transaction<br>traceability<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>equipment:mes</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/L02_COMPLETE_WORK_ORDER.json</code></td>
    </tr>
    <tr>
      <td>L03</td>
      <td><code>REPORT_OPERATION_RESULT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>MES, WMS, traceability, work order, evidence 기록을 수행하는 digital task입니다.</td>
      <td>operation*: Any<br>result*: Any</td>
      <td>digital_transaction<br>traceability<br>equipment_interaction</td>
      <td>equipment:mes<br>equipment:scada<br>equipment:erp</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/L03_REPORT_OPERATION_RESULT.json</code></td>
    </tr>
    <tr>
      <td>L04</td>
      <td><code>REGISTER_TRACEABILITY</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>MES, WMS, traceability, work order, evidence 기록을 수행하는 digital task입니다.</td>
      <td>entity*: EntityRef | str<br>traceability_data*: Any</td>
      <td>digital_transaction<br>traceability<br>tool_use<br>equipment_interaction</td>
      <td>tool:scanner<br>tool:rfid<br>equipment:mes<br>equipment:qms<br>equipment:traceability_system</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/L04_REGISTER_TRACEABILITY.json</code></td>
    </tr>
    <tr>
      <td>L05</td>
      <td><code>CREATE_EXCEPTION_REPORT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>MES, WMS, traceability, work order, evidence 기록을 수행하는 digital task입니다.</td>
      <td>exception_type*: Any<br>target*: Any<br>details*: Any<br>evidence*: Any</td>
      <td>digital_transaction<br>traceability<br>tool_use<br>equipment_interaction</td>
      <td>tool:camera<br>equipment:qms<br>equipment:cmms<br>equipment:ehs<br>equipment:mes</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/L05_CREATE_EXCEPTION_REPORT.json</code></td>
    </tr>
    <tr>
      <td>L06</td>
      <td><code>CAPTURE_EVIDENCE_OR_STATUS</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>MES, WMS, traceability, work order, evidence 기록을 수행하는 digital task입니다.</td>
      <td>target*: Any<br>evidence_spec*: Any</td>
      <td>digital_transaction<br>traceability<br>tool_use<br>equipment_interaction</td>
      <td>tool:camera<br>tool:scanner<br>tool:sensor<br>equipment:camera<br>equipment:sensor<br>equipment:storage_system</td>
      <td>LOW</td>
      <td><code>READ_CONTEXT</code><br><code>CREATE_OR_UPDATE_RECORD</code><br><code>VERIFY_TRANSACTION</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/L06_CAPTURE_EVIDENCE_OR_STATUS.json</code></td>
    </tr>
    <tr>
      <td>M01</td>
      <td><code>FETCH_FOR_OPERATOR</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>operator나 다른 휴머노이드와 handover, 수령, 협업, 보조 운반을 수행하는 task입니다.</td>
      <td>request*: Any<br>operator_or_station*: LocationRef | str</td>
      <td>human_collaboration<br>handover<br>safe_interaction<br>tool_use<br>vehicle_operation<br>equipment_interaction</td>
      <td>tool:scanner<br>vehicle:cart<br>vehicle:amr<br>equipment:source_location<br>equipment:operator_station</td>
      <td>LOW</td>
      <td><code>TRANSFER</code> [ATOMIC_TASK]<br><code>HANDOVER_ITEM</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/M01_FETCH_FOR_OPERATOR.json</code></td>
    </tr>
    <tr>
      <td>M02</td>
      <td><code>HANDOVER_ITEM</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>operator나 다른 휴머노이드와 handover, 수령, 협업, 보조 운반을 수행하는 task입니다.</td>
      <td>item*: EntityRef | str<br>recipient*: Any<br>handover_spec*: Any</td>
      <td>human_collaboration<br>handover<br>safe_interaction<br>equipment_interaction</td>
      <td>equipment:operator<br>equipment:robot<br>equipment:item</td>
      <td>MEDIUM</td>
      <td><code>NAVIGATE_TO</code><br><code>ANNOUNCE_INTENT</code><br><code>EXECUTE_HUMAN_COLLABORATION_ACTION</code><br><code>CONFIRM_OPERATOR_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/M02_HANDOVER_ITEM.json</code></td>
    </tr>
    <tr>
      <td>M03</td>
      <td><code>RECEIVE_FROM_OPERATOR</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>operator나 다른 휴머노이드와 handover, 수령, 협업, 보조 운반을 수행하는 task입니다.</td>
      <td>item_spec*: EntityRef | str<br>operator*: Any<br>receive_spec*: Any</td>
      <td>human_collaboration<br>handover<br>safe_interaction<br>equipment_interaction</td>
      <td>equipment:operator<br>equipment:item</td>
      <td>MEDIUM</td>
      <td><code>NAVIGATE_TO</code><br><code>ANNOUNCE_INTENT</code><br><code>EXECUTE_HUMAN_COLLABORATION_ACTION</code><br><code>CONFIRM_OPERATOR_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/M03_RECEIVE_FROM_OPERATOR.json</code></td>
    </tr>
    <tr>
      <td>M04</td>
      <td><code>HANDOVER_TOOL</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>operator나 다른 휴머노이드와 handover, 수령, 협업, 보조 운반을 수행하는 task입니다.</td>
      <td>tool*: EntityRef | str<br>operator*: Any<br>action*: Any<br>handover_spec*: Any</td>
      <td>human_collaboration<br>handover<br>safe_interaction<br>tool_use<br>equipment_interaction</td>
      <td>tool:tool<br>equipment:operator<br>equipment:tool</td>
      <td>MEDIUM</td>
      <td><code>NAVIGATE_TO</code><br><code>ANNOUNCE_INTENT</code><br><code>EXECUTE_HUMAN_COLLABORATION_ACTION</code><br><code>CONFIRM_OPERATOR_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/M04_HANDOVER_TOOL.json</code></td>
    </tr>
    <tr>
      <td>M05</td>
      <td><code>HOLD_OR_POSITION_FOR_OPERATOR</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>operator나 다른 휴머노이드와 handover, 수령, 협업, 보조 운반을 수행하는 task입니다.</td>
      <td>item*: EntityRef | str<br>pose_or_constraint*: Any<br>operator*: Any</td>
      <td>human_collaboration<br>handover<br>safe_interaction<br>equipment_interaction</td>
      <td>equipment:operator<br>equipment:part<br>equipment:fixture</td>
      <td>MEDIUM</td>
      <td><code>NAVIGATE_TO</code><br><code>ANNOUNCE_INTENT</code><br><code>EXECUTE_HUMAN_COLLABORATION_ACTION</code><br><code>CONFIRM_OPERATOR_STATE</code><br><code>LOG_RESULT</code></td>
      <td><code>data/tasks/M05_HOLD_OR_POSITION_FOR_OPERATOR.json</code></td>
    </tr>
    <tr>
      <td>M06</td>
      <td><code>ASSIST_OPERATOR_MOVE_OR_LIFT</code></td>
      <td><code>COMPOSITE_TASK</code></td>
      <td>operator나 다른 휴머노이드와 handover, 수령, 협업, 보조 운반을 수행하는 task입니다.</td>
      <td>item*: EntityRef | str<br>operator*: Any<br>source*: LocationRef | str<br>destination*: LocationRef | str</td>
      <td>human_collaboration<br>handover<br>safe_interaction<br>tool_use<br>vehicle_operation<br>equipment_interaction<br>high_risk_task</td>
      <td>tool:lifting_aid<br>vehicle:cart<br>equipment:operator<br>equipment:item<br>equipment:path</td>
      <td>HIGH</td>
      <td><code>TRANSFER</code> [ATOMIC_TASK]<br><code>HANDOVER_ITEM</code> [ATOMIC_TASK]</td>
      <td><code>data/tasks/M06_ASSIST_OPERATOR_MOVE_OR_LIFT.json</code></td>
    </tr>
    <tr>
      <td>S01</td>
      <td><code>WELD_SEAM</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>선박 section 또는 exterior surface tile을 대상으로 용접, 표면처리, sealant 적용, 도장, 품질 확인을 수행하는 shipyard task입니다.</td>
      <td>ship_section*: Any<br>weld_spec*: Any</td>
      <td>welding<br>surface_localization<br>tool_use<br>inspection<br>digital_recording</td>
      <td>tool:welding_tool<br>tool:inspection_camera<br>equipment:ship_section<br>equipment:fixture</td>
      <td>HIGH</td>
      <td><code>CHECK_SAFETY_ZONE</code><br><code>LOCALIZE_SURFACE</code><br><code>FIX_OR_HOLD_PART</code><br><code>OPERATE_TOOL</code><br><code>PROCESS_FEATURE_OR_SURFACE</code><br><code>INSPECT_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/S01_WELD_SEAM.json</code></td>
    </tr>
    <tr>
      <td>S02</td>
      <td><code>PAINT_SURFACE</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>선박 section 또는 exterior surface tile을 대상으로 용접, 표면처리, sealant 적용, 도장, 품질 확인을 수행하는 shipyard task입니다.</td>
      <td>ship_section*: Any<br>paint_spec*: Any</td>
      <td>material_application<br>surface_preparation<br>tool_use<br>equipment_interaction<br>digital_recording</td>
      <td>tool:paint_dispenser<br>tool:coverage_sensor<br>equipment:ship_section<br>equipment:paint_supply</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_SURFACE</code><br><code>PRIMITIVE_PREPARE_SURFACE</code><br><code>OPERATE_TOOL_OR_DISPENSER</code><br><code>PRIMITIVE_APPLY_MATERIAL</code><br><code>VERIFY_COVERAGE_OR_AMOUNT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/S02_PAINT_SURFACE.json</code></td>
    </tr>
    <tr>
      <td>S03</td>
      <td><code>APPLY_SEALANT</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>선박 section 또는 exterior surface tile을 대상으로 용접, 표면처리, sealant 적용, 도장, 품질 확인을 수행하는 shipyard task입니다.</td>
      <td>ship_section*: Any<br>sealant_spec*: Any</td>
      <td>material_application<br>tool_use<br>surface_preparation<br>inspection<br>digital_recording</td>
      <td>tool:sealant_dispenser<br>tool:coverage_sensor<br>equipment:ship_section<br>equipment:sealant_supply</td>
      <td>MEDIUM</td>
      <td><code>LOCALIZE_SURFACE</code><br><code>PRIMITIVE_PREPARE_SURFACE</code><br><code>OPERATE_TOOL_OR_DISPENSER</code><br><code>PRIMITIVE_APPLY_MATERIAL</code><br><code>VERIFY_COVERAGE_OR_AMOUNT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/S03_APPLY_SEALANT.json</code></td>
    </tr>
    <tr>
      <td>S04</td>
      <td><code>VERIFY_SHIP_SECTION</code></td>
      <td><code>ATOMIC_TASK</code></td>
      <td>선박 section 또는 exterior surface tile을 대상으로 용접, 표면처리, sealant 적용, 도장, 품질 확인을 수행하는 shipyard task입니다.</td>
      <td>ship_section*: Any<br>verification_plan*: Any</td>
      <td>inspection<br>measurement<br>digital_recording<br>tool_use<br>equipment_interaction</td>
      <td>tool:inspection_camera<br>tool:gauge<br>equipment:ship_section</td>
      <td>LOW</td>
      <td><code>PRIMITIVE_IDENTIFY_ITEM</code><br><code>LOCALIZE_OBJECT</code><br><code>EXECUTE_QUALITY_ACTION</code><br><code>CLASSIFY_RESULT</code><br><code>RECORD_RESULT</code></td>
      <td><code>data/tasks/S04_VERIFY_SHIP_SECTION.json</code></td>
    </tr>
  </tbody>
</table>
