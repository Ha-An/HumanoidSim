cmake_minimum_required(VERSION 3.8)
project(humanoidsim_ros_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/ExecuteTask.action"
  "action/ExecutePrimitive.action"
  "action/RecoverIncident.action"
  "srv/ExpandTask.srv"
  "srv/ValidateTransition.srv"
  "srv/InjectIncident.srv"
  "srv/GetIncidentProtocol.srv"
  "srv/PlayTrace.srv"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
