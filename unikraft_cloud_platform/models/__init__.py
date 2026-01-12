"""Contains all the data models used in inputs/outputs"""

from .attach_volume_by_uuid_request_body import AttachVolumeByUUIDRequestBody
from .attach_volumes_request import AttachVolumesRequest
from .attach_volumes_request_instance_id import AttachVolumesRequestInstanceID
from .attach_volumes_response import AttachVolumesResponse
from .attach_volumes_response_attached_volume import AttachVolumesResponseAttachedVolume
from .attach_volumes_response_data import AttachVolumesResponseData
from .autoscale_policy import AutoscalePolicy
from .autoscale_policy_adjustment_type import AutoscalePolicyAdjustmentType
from .autoscale_policy_metric import AutoscalePolicyMetric
from .autoscale_policy_step import AutoscalePolicyStep
from .body_instance_id import BodyInstanceID
from .certificate import Certificate
from .certificate_state import CertificateState
from .configuration_instance_create_args import ConfigurationInstanceCreateArgs
from .create_autoscale_configuration_by_service_group_uuid_request import (
    CreateAutoscaleConfigurationByServiceGroupUUIDRequest,
)
from .create_autoscale_configuration_by_service_group_uuid_request_instance_create_args import (
    CreateAutoscaleConfigurationByServiceGroupUUIDRequestInstanceCreateArgs,
)
from .create_autoscale_configuration_policy_request import CreateAutoscaleConfigurationPolicyRequest
from .create_autoscale_configuration_policy_response import CreateAutoscaleConfigurationPolicyResponse
from .create_autoscale_configuration_policy_response_data import CreateAutoscaleConfigurationPolicyResponseData
from .create_autoscale_configuration_policy_response_policy import CreateAutoscaleConfigurationPolicyResponsePolicy
from .create_autoscale_configurations_request_configuration import CreateAutoscaleConfigurationsRequestConfiguration
from .create_autoscale_configurations_response import CreateAutoscaleConfigurationsResponse
from .create_autoscale_configurations_response_configurations_response import (
    CreateAutoscaleConfigurationsResponseConfigurationsResponse,
)
from .create_autoscale_configurations_response_data import CreateAutoscaleConfigurationsResponseData
from .create_certificate_request import CreateCertificateRequest
from .create_certificate_response import CreateCertificateResponse
from .create_certificate_response_data import CreateCertificateResponseData
from .create_instance_request import CreateInstanceRequest
from .create_instance_request_domain import CreateInstanceRequestDomain
from .create_instance_request_env import CreateInstanceRequestEnv
from .create_instance_request_features_item import CreateInstanceRequestFeaturesItem
from .create_instance_request_restart_policy import CreateInstanceRequestRestartPolicy
from .create_instance_request_service_group import CreateInstanceRequestServiceGroup
from .create_instance_request_volume import CreateInstanceRequestVolume
from .create_instance_response import CreateInstanceResponse
from .create_instance_response_data import CreateInstanceResponseData
from .create_service_group_request import CreateServiceGroupRequest
from .create_service_group_request_domain import CreateServiceGroupRequestDomain
from .create_service_group_response import CreateServiceGroupResponse
from .create_service_group_response_data import CreateServiceGroupResponseData
from .create_volume_request import CreateVolumeRequest
from .create_volume_response import CreateVolumeResponse
from .create_volume_response_data import CreateVolumeResponseData
from .create_volume_response_volume import CreateVolumeResponseVolume
from .delete_autoscale_configuration_policy_response import DeleteAutoscaleConfigurationPolicyResponse
from .delete_autoscale_configuration_policy_response_data import DeleteAutoscaleConfigurationPolicyResponseData
from .delete_autoscale_configuration_policy_response_policies_response import (
    DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse,
)
from .delete_autoscale_configurations_response import DeleteAutoscaleConfigurationsResponse
from .delete_autoscale_configurations_response_data import DeleteAutoscaleConfigurationsResponseData
from .delete_autoscale_configurations_response_service_group import DeleteAutoscaleConfigurationsResponseServiceGroup
from .delete_certificates_response import DeleteCertificatesResponse
from .delete_certificates_response_data import DeleteCertificatesResponseData
from .delete_certificates_response_deleted_certificate import DeleteCertificatesResponseDeletedCertificate
from .delete_instances_response import DeleteInstancesResponse
from .delete_instances_response_data import DeleteInstancesResponseData
from .delete_instances_response_deleted_instance import DeleteInstancesResponseDeletedInstance
from .delete_policy_request import DeletePolicyRequest
from .delete_service_groups_response import DeleteServiceGroupsResponse
from .delete_service_groups_response_data import DeleteServiceGroupsResponseData
from .delete_service_groups_response_deleted_service_group import DeleteServiceGroupsResponseDeletedServiceGroup
from .delete_volumes_response import DeleteVolumesResponse
from .delete_volumes_response_data import DeleteVolumesResponseData
from .delete_volumes_response_deleted_volume import DeleteVolumesResponseDeletedVolume
from .detach_volume_by_uuid_request_body import DetachVolumeByUUIDRequestBody
from .detach_volumes_request import DetachVolumesRequest
from .detach_volumes_request_instance_id import DetachVolumesRequestInstanceID
from .detach_volumes_response import DetachVolumesResponse
from .detach_volumes_response_data import DetachVolumesResponseData
from .detach_volumes_response_detached_volume import DetachVolumesResponseDetachedVolume
from .domain import Domain
from .get_autoscale_configuration_policy_request import GetAutoscaleConfigurationPolicyRequest
from .get_autoscale_configuration_policy_response import GetAutoscaleConfigurationPolicyResponse
from .get_autoscale_configuration_policy_response_data import GetAutoscaleConfigurationPolicyResponseData
from .get_autoscale_configuration_policy_response_policy_response import (
    GetAutoscaleConfigurationPolicyResponsePolicyResponse,
)
from .get_autoscale_configurations_response import GetAutoscaleConfigurationsResponse
from .get_autoscale_configurations_response_data import GetAutoscaleConfigurationsResponseData
from .get_autoscale_configurations_response_service_group import GetAutoscaleConfigurationsResponseServiceGroup
from .get_autoscale_configurations_response_status import GetAutoscaleConfigurationsResponseStatus
from .get_certificates_response import GetCertificatesResponse
from .get_certificates_response_data import GetCertificatesResponseData
from .get_image_response import GetImageResponse
from .get_image_response_data import GetImageResponseData
from .get_instance_logs_by_uuid_request_body import GetInstanceLogsByUUIDRequestBody
from .get_instance_logs_request import GetInstanceLogsRequest
from .get_instance_logs_response import GetInstanceLogsResponse
from .get_instance_logs_response_available import GetInstanceLogsResponseAvailable
from .get_instance_logs_response_data import GetInstanceLogsResponseData
from .get_instance_logs_response_logged_instance import GetInstanceLogsResponseLoggedInstance
from .get_instance_logs_response_logged_instance_state import GetInstanceLogsResponseLoggedInstanceState
from .get_instance_logs_response_range import GetInstanceLogsResponseRange
from .get_instance_metrics_response import GetInstanceMetricsResponse
from .get_instance_metrics_response_data import GetInstanceMetricsResponseData
from .get_instance_metrics_response_instance_metrics import GetInstanceMetricsResponseInstanceMetrics
from .get_instances_response import GetInstancesResponse
from .get_instances_response_data import GetInstancesResponseData
from .get_service_groups_response import GetServiceGroupsResponse
from .get_service_groups_response_data import GetServiceGroupsResponseData
from .get_volumes_response import GetVolumesResponse
from .get_volumes_response_data import GetVolumesResponseData
from .healthz_response import HealthzResponse
from .healthz_response_data import HealthzResponseData
from .healthz_response_data_services import HealthzResponseDataServices
from .image import Image
from .image_labels import ImageLabels
from .instance import Instance
from .instance_create_args_instance_create_request_roms import InstanceCreateArgsInstanceCreateRequestRoms
from .instance_env import InstanceEnv
from .instance_instance_service_group import InstanceInstanceServiceGroup
from .instance_instance_volume import InstanceInstanceVolume
from .instance_network_interface import InstanceNetworkInterface
from .instance_restart_policy import InstanceRestartPolicy
from .instance_scale_to_zero import InstanceScaleToZero
from .instance_scale_to_zero_policy import InstanceScaleToZeroPolicy
from .instance_service_group_instance_domain import InstanceServiceGroupInstanceDomain
from .instance_state import InstanceState
from .name_or_uuid import NameOrUUID
from .object_ import Object
from .quotas import Quotas
from .quotas_limits import QuotasLimits
from .quotas_response import QuotasResponse
from .quotas_response_data import QuotasResponseData
from .quotas_stats import QuotasStats
from .response_error import ResponseError
from .response_status import ResponseStatus
from .service import Service
from .service_group import ServiceGroup
from .service_group_instance import ServiceGroupInstance
from .service_group_template import ServiceGroupTemplate
from .service_handlers_item import ServiceHandlersItem
from .start_instance_response import StartInstanceResponse
from .start_instance_response_data import StartInstanceResponseData
from .start_instance_response_started_instance import StartInstanceResponseStartedInstance
from .stop_instance_response import StopInstanceResponse
from .stop_instance_response_data import StopInstanceResponseData
from .stop_instance_response_stopped_instance import StopInstanceResponseStoppedInstance
from .stop_instance_response_stopped_instance_previous_state import StopInstanceResponseStoppedInstancePreviousState
from .stop_instance_response_stopped_instance_state import StopInstanceResponseStoppedInstanceState
from .stop_instances_request_id import StopInstancesRequestID
from .update_instance_by_uuid_request_body import UpdateInstanceByUUIDRequestBody
from .update_instance_by_uuid_request_body_op import UpdateInstanceByUUIDRequestBodyOp
from .update_instance_by_uuid_request_body_prop import UpdateInstanceByUUIDRequestBodyProp
from .update_instances_request import UpdateInstancesRequest
from .update_instances_request_op import UpdateInstancesRequestOp
from .update_instances_request_prop import UpdateInstancesRequestProp
from .update_instances_response import UpdateInstancesResponse
from .update_instances_response_data import UpdateInstancesResponseData
from .update_instances_response_updated_instance import UpdateInstancesResponseUpdatedInstance
from .update_service_group_by_uuid_request_body import UpdateServiceGroupByUUIDRequestBody
from .update_service_group_by_uuid_request_body_op import UpdateServiceGroupByUUIDRequestBodyOp
from .update_service_group_by_uuid_request_body_prop import UpdateServiceGroupByUUIDRequestBodyProp
from .update_service_groups_request_item import UpdateServiceGroupsRequestItem
from .update_service_groups_request_item_op import UpdateServiceGroupsRequestItemOp
from .update_service_groups_request_item_prop import UpdateServiceGroupsRequestItemProp
from .update_service_groups_response import UpdateServiceGroupsResponse
from .update_service_groups_response_data import UpdateServiceGroupsResponseData
from .update_service_groups_response_updated_service_group import UpdateServiceGroupsResponseUpdatedServiceGroup
from .update_volume_by_uuid_request_body import UpdateVolumeByUUIDRequestBody
from .update_volume_by_uuid_request_body_op import UpdateVolumeByUUIDRequestBodyOp
from .update_volume_by_uuid_request_body_prop import UpdateVolumeByUUIDRequestBodyProp
from .update_volumes_request_item import UpdateVolumesRequestItem
from .update_volumes_request_item_op import UpdateVolumesRequestItemOp
from .update_volumes_request_item_prop import UpdateVolumesRequestItemProp
from .update_volumes_response import UpdateVolumesResponse
from .update_volumes_response_data import UpdateVolumesResponseData
from .update_volumes_response_updated_volume import UpdateVolumesResponseUpdatedVolume
from .volume import Volume
from .volume_instance_id import VolumeInstanceID
from .volume_state import VolumeState
from .volume_volume_instance_mount import VolumeVolumeInstanceMount
from .wait_instance_by_uuid_request_body import WaitInstanceByUUIDRequestBody
from .wait_instance_by_uuid_request_body_state import WaitInstanceByUUIDRequestBodyState
from .wait_instance_response import WaitInstanceResponse
from .wait_instance_response_data import WaitInstanceResponseData
from .wait_instance_response_waited_instance import WaitInstanceResponseWaitedInstance
from .wait_instance_response_waited_instance_state import WaitInstanceResponseWaitedInstanceState
from .wait_instances_state import WaitInstancesState

__all__ = (
    "AttachVolumeByUUIDRequestBody",
    "AttachVolumesRequest",
    "AttachVolumesRequestInstanceID",
    "AttachVolumesResponse",
    "AttachVolumesResponseAttachedVolume",
    "AttachVolumesResponseData",
    "AutoscalePolicy",
    "AutoscalePolicyAdjustmentType",
    "AutoscalePolicyMetric",
    "AutoscalePolicyStep",
    "BodyInstanceID",
    "Certificate",
    "CertificateState",
    "ConfigurationInstanceCreateArgs",
    "CreateAutoscaleConfigurationByServiceGroupUUIDRequest",
    "CreateAutoscaleConfigurationByServiceGroupUUIDRequestInstanceCreateArgs",
    "CreateAutoscaleConfigurationPolicyRequest",
    "CreateAutoscaleConfigurationPolicyResponse",
    "CreateAutoscaleConfigurationPolicyResponseData",
    "CreateAutoscaleConfigurationPolicyResponsePolicy",
    "CreateAutoscaleConfigurationsRequestConfiguration",
    "CreateAutoscaleConfigurationsResponse",
    "CreateAutoscaleConfigurationsResponseConfigurationsResponse",
    "CreateAutoscaleConfigurationsResponseData",
    "CreateCertificateRequest",
    "CreateCertificateResponse",
    "CreateCertificateResponseData",
    "CreateInstanceRequest",
    "CreateInstanceRequestDomain",
    "CreateInstanceRequestEnv",
    "CreateInstanceRequestFeaturesItem",
    "CreateInstanceRequestRestartPolicy",
    "CreateInstanceRequestServiceGroup",
    "CreateInstanceRequestVolume",
    "CreateInstanceResponse",
    "CreateInstanceResponseData",
    "CreateServiceGroupRequest",
    "CreateServiceGroupRequestDomain",
    "CreateServiceGroupResponse",
    "CreateServiceGroupResponseData",
    "CreateVolumeRequest",
    "CreateVolumeResponse",
    "CreateVolumeResponseData",
    "CreateVolumeResponseVolume",
    "DeleteAutoscaleConfigurationPolicyResponse",
    "DeleteAutoscaleConfigurationPolicyResponseData",
    "DeleteAutoscaleConfigurationPolicyResponsePoliciesResponse",
    "DeleteAutoscaleConfigurationsResponse",
    "DeleteAutoscaleConfigurationsResponseData",
    "DeleteAutoscaleConfigurationsResponseServiceGroup",
    "DeleteCertificatesResponse",
    "DeleteCertificatesResponseData",
    "DeleteCertificatesResponseDeletedCertificate",
    "DeleteInstancesResponse",
    "DeleteInstancesResponseData",
    "DeleteInstancesResponseDeletedInstance",
    "DeletePolicyRequest",
    "DeleteServiceGroupsResponse",
    "DeleteServiceGroupsResponseData",
    "DeleteServiceGroupsResponseDeletedServiceGroup",
    "DeleteVolumesResponse",
    "DeleteVolumesResponseData",
    "DeleteVolumesResponseDeletedVolume",
    "DetachVolumeByUUIDRequestBody",
    "DetachVolumesRequest",
    "DetachVolumesRequestInstanceID",
    "DetachVolumesResponse",
    "DetachVolumesResponseData",
    "DetachVolumesResponseDetachedVolume",
    "Domain",
    "GetAutoscaleConfigurationPolicyRequest",
    "GetAutoscaleConfigurationPolicyResponse",
    "GetAutoscaleConfigurationPolicyResponseData",
    "GetAutoscaleConfigurationPolicyResponsePolicyResponse",
    "GetAutoscaleConfigurationsResponse",
    "GetAutoscaleConfigurationsResponseData",
    "GetAutoscaleConfigurationsResponseServiceGroup",
    "GetAutoscaleConfigurationsResponseStatus",
    "GetCertificatesResponse",
    "GetCertificatesResponseData",
    "GetImageResponse",
    "GetImageResponseData",
    "GetInstanceLogsByUUIDRequestBody",
    "GetInstanceLogsRequest",
    "GetInstanceLogsResponse",
    "GetInstanceLogsResponseAvailable",
    "GetInstanceLogsResponseData",
    "GetInstanceLogsResponseLoggedInstance",
    "GetInstanceLogsResponseLoggedInstanceState",
    "GetInstanceLogsResponseRange",
    "GetInstanceMetricsResponse",
    "GetInstanceMetricsResponseData",
    "GetInstanceMetricsResponseInstanceMetrics",
    "GetInstancesResponse",
    "GetInstancesResponseData",
    "GetServiceGroupsResponse",
    "GetServiceGroupsResponseData",
    "GetVolumesResponse",
    "GetVolumesResponseData",
    "HealthzResponse",
    "HealthzResponseData",
    "HealthzResponseDataServices",
    "Image",
    "ImageLabels",
    "Instance",
    "InstanceCreateArgsInstanceCreateRequestRoms",
    "InstanceEnv",
    "InstanceInstanceServiceGroup",
    "InstanceInstanceVolume",
    "InstanceNetworkInterface",
    "InstanceRestartPolicy",
    "InstanceScaleToZero",
    "InstanceScaleToZeroPolicy",
    "InstanceServiceGroupInstanceDomain",
    "InstanceState",
    "NameOrUUID",
    "Object",
    "Quotas",
    "QuotasLimits",
    "QuotasResponse",
    "QuotasResponseData",
    "QuotasStats",
    "ResponseError",
    "ResponseStatus",
    "Service",
    "ServiceGroup",
    "ServiceGroupInstance",
    "ServiceGroupTemplate",
    "ServiceHandlersItem",
    "StartInstanceResponse",
    "StartInstanceResponseData",
    "StartInstanceResponseStartedInstance",
    "StopInstanceResponse",
    "StopInstanceResponseData",
    "StopInstanceResponseStoppedInstance",
    "StopInstanceResponseStoppedInstancePreviousState",
    "StopInstanceResponseStoppedInstanceState",
    "StopInstancesRequestID",
    "UpdateInstanceByUUIDRequestBody",
    "UpdateInstanceByUUIDRequestBodyOp",
    "UpdateInstanceByUUIDRequestBodyProp",
    "UpdateInstancesRequest",
    "UpdateInstancesRequestOp",
    "UpdateInstancesRequestProp",
    "UpdateInstancesResponse",
    "UpdateInstancesResponseData",
    "UpdateInstancesResponseUpdatedInstance",
    "UpdateServiceGroupByUUIDRequestBody",
    "UpdateServiceGroupByUUIDRequestBodyOp",
    "UpdateServiceGroupByUUIDRequestBodyProp",
    "UpdateServiceGroupsRequestItem",
    "UpdateServiceGroupsRequestItemOp",
    "UpdateServiceGroupsRequestItemProp",
    "UpdateServiceGroupsResponse",
    "UpdateServiceGroupsResponseData",
    "UpdateServiceGroupsResponseUpdatedServiceGroup",
    "UpdateVolumeByUUIDRequestBody",
    "UpdateVolumeByUUIDRequestBodyOp",
    "UpdateVolumeByUUIDRequestBodyProp",
    "UpdateVolumesRequestItem",
    "UpdateVolumesRequestItemOp",
    "UpdateVolumesRequestItemProp",
    "UpdateVolumesResponse",
    "UpdateVolumesResponseData",
    "UpdateVolumesResponseUpdatedVolume",
    "Volume",
    "VolumeInstanceID",
    "VolumeState",
    "VolumeVolumeInstanceMount",
    "WaitInstanceByUUIDRequestBody",
    "WaitInstanceByUUIDRequestBodyState",
    "WaitInstanceResponse",
    "WaitInstanceResponseData",
    "WaitInstanceResponseWaitedInstance",
    "WaitInstanceResponseWaitedInstanceState",
    "WaitInstancesState",
)
