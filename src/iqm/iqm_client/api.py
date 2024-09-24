from enum import Enum, auto

class APIEndpoint(Enum):
    CONFIGURATION = auto()
    QUALITYT_METRICS_LATEST = auto()
    QUALITYT_METRICS_MONITORING = auto()
    SUBMIT_JOB = auto()
    GET_JOB_REQUEST_PARAMETERS = auto()
    GET_JOB_RESULT = auto()
    GET_JOB_STATUS = auto()
    GET_JOB_CALIBRATION_SET_ID = auto()
    GET_JOB_CIRCUITS_BATCH = auto()
    GET_JOB_TIMELINE = auto()
    GET_JOB_ERROR_LOG = auto()
    GET_JOB_COUNTS = auto()
    ABORT_JOB = auto()
    DELETE_JOB = auto()
    QUANTUM_ARCHITECTURE = auto()
    CALIBRATED_GATES = auto()
    HEALTH = auto()
    ABOUT = auto()

class APIVariant(Enum):
    V1 = "V1"  # Cocos-based circuits execution, including Resonance
    V2 = "V2"  # Station-Control-based circuits execution
    RESONANCE_V1 = "RESONANCE_V1"

class APIConfig:
    def __init__(self, variant: APIVariant, iqm_server_url: str):
        """
        Args:
            variant: API variant.
            iqm_server_url: URL of the IQM server, e.g. https://test.qc.iqm.fi or https://cocos.resonance.meetiqm.com/garnet
        """
        self.variant = variant
        self.iqm_server_url = iqm_server_url
        self.urls = self._get_api_urls()

    def _get_api_urls(self) -> dict[APIEndpoint, str]:
        """
        Returns:
            Relative URLs for each supported API endpoints.
        """
        if self.variant == APIVariant.V1:
            return {
                APIEndpoint.CONFIGURATION: "/configuration",
                APIEndpoint.QUALITYT_METRICS_LATEST: "/calibration/metrics/latest",
                APIEndpoint.SUBMIT_JOB: "/jobs",
                APIEndpoint.GET_JOB_RESULT: "/jobs/%s",
                APIEndpoint.GET_JOB_STATUS: "/jobs/%s/status",
                APIEndpoint.ABORT_JOB: "/jobs/%s/abort",
                APIEndpoint.DELETE_JOB: "/jobs/%s",
                APIEndpoint.QUANTUM_ARCHITECTURE: "/quantum-architecture",
                APIEndpoint.CALIBRATED_GATES: "/api/v1/calibration/%s/gates",
                APIEndpoint.QUALITYT_METRICS_MONITORING: "/api/v1/monitor/calibration/metrics",
                APIEndpoint.HEALTH: "/health",
                APIEndpoint.ABOUT: "/about",
            }
        elif self.variant == APIVariant.RESONANCE_V1:
            # Resonance provides a subset of the V1 API
            return {
                APIEndpoint.SUBMIT_JOB: "/jobs",
                APIEndpoint.GET_JOB_RESULT: "/jobs/%s",
                APIEndpoint.GET_JOB_STATUS: "/jobs/%s/status",
                APIEndpoint.ABORT_JOB: "/jobs/%s/abort",
                APIEndpoint.DELETE_JOB: "/jobs/%s",
                APIEndpoint.QUANTUM_ARCHITECTURE: "/quantum-architecture",
                APIEndpoint.CALIBRATED_GATES: "/api/v1/calibration/%s/gates",
            }
        elif self.variant == APIVariant.V2:
            return {
                APIEndpoint.GET_JOB_REQUEST_PARAMETERS: "/station/circuits/%s/request_parameters",
                APIEndpoint.CONFIGURATION: "/cocos/configuration",  # TODO: should be /station/configuration
                APIEndpoint.QUALITYT_METRICS_LATEST: "/cocos/calibration/metrics/latest",
                APIEndpoint.SUBMIT_JOB: "/station/circuits",
                APIEndpoint.GET_JOB_RESULT: "/station/circuits/%s/measurements",
                APIEndpoint.GET_JOB_STATUS: "/station/circuits/%s/status",
                APIEndpoint.GET_JOB_CALIBRATION_SET_ID: "/station/circuits/%s/calibration_set_id",
                APIEndpoint.GET_JOB_CIRCUITS_BATCH: "/station/circuits/%s/circuits_batch",
                APIEndpoint.GET_JOB_TIMELINE: "/station/circuits/%s/timeline",
                APIEndpoint.GET_JOB_ERROR_LOG: "/station/circuits/%s/error_log",
                APIEndpoint.GET_JOB_COUNTS: "/station/circuits/%s/counts",
                APIEndpoint.ABORT_JOB: "/station/circuits/%s/abort",
                APIEndpoint.DELETE_JOB: "/station/circuits/%s",
                APIEndpoint.QUANTUM_ARCHITECTURE: "/cocos/quantum-architecture",
                APIEndpoint.CALIBRATED_GATES: "/cocos/api/v1/calibration/%s/gates",
                APIEndpoint.QUALITYT_METRICS_MONITORING: "/cocos/api/v1/monitor/calibration/metrics",
                APIEndpoint.HEALTH: "/cocos/health",
                APIEndpoint.ABOUT: "/cocos/about",
            }
        else:
            raise ValueError(f"Unsupported API variant: {self.variant}")

    def is_supported(self, endpoint: APIEndpoint) -> bool:
        """
        Args:
            endpoint: API endpoint.

        Returns:
            True if the endpoint is supported, False otherwise.
        """
        return endpoint in self.urls

    def url(self, endpoint: APIEndpoint, *args) -> str:
        """
        Args:
            endpoint: API endpoint.

        Returns:
            URL for the given endpoint or None if the endpoint is not supported.
        """
        url = self.urls.get(endpoint)
        if url is None:
            raise ValueError(f"Unsupported API endpoint: {endpoint}")
        return f"{self.iqm_server_url}/{url % args}"
