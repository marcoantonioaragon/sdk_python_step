import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sdk_python_step.variation_assigner.step_python_local import VariationAssigner


class ExperimentServiceError(Exception):
    pass


class RemoteRequestError(ExperimentServiceError):
    pass


class ExposurePostError(ExperimentServiceError):
    pass


class Requester:
    def get_json(self, url: str) -> Dict[str, Any]:
        raise NotImplementedError

    def post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class UrlRequester(Requester):
    def get_json(self, url: str) -> Dict[str, Any]:
        request = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return json.load(response)
        except (HTTPError, URLError) as exc:
            raise RemoteRequestError(f"Failed to fetch config from {url}: {exc}") from exc

    def post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                return json.load(response)
        except (HTTPError, URLError) as exc:
            raise ExposurePostError(f"Failed to post exposure to {url}: {exc}") from exc


@dataclass
class VariantDefinition:
    id: int
    name: str
    allocation: float
    is_control: bool = False
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentConfig:
    change_id: str
    experiment_id: str
    traffic_allocation: float
    variants: List[VariantDefinition]
    properties: List[str] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, change_id: str, response: Dict[str, Any]) -> "ExperimentConfig":
        experiment_id = response.get("experiment_id")
        if experiment_id is None:
            raise ExperimentServiceError("API response missing experiment_id")

        traffic_allocation = float(response.get("traffic_allocation", 1.0))
        raw_variants = response.get("variants", [])
        properties = response.get("properties", []) or []

        variants: List[VariantDefinition] = []
        for index, raw_variant in enumerate(raw_variants):
            variant_id = raw_variant.get("id", index)
            variant_name = str(raw_variant.get("name", variant_id))
            allocation = float(raw_variant.get("allocation", 0.0))
            is_control = bool(raw_variant.get("is_control", False))
            variant_properties = raw_variant.get("properties", {}) or {}
            variants.append(
                VariantDefinition(
                    id=int(variant_id),
                    name=variant_name,
                    allocation=allocation,
                    is_control=is_control,
                    properties=dict(variant_properties),
                )
            )

        if len(variants) == 0:
            raise ExperimentServiceError("API response must include at least one variant")

        return cls(
            change_id=change_id,
            experiment_id=experiment_id,
            traffic_allocation=traffic_allocation,
            variants=variants,
            properties=[str(p) for p in properties],
        )

    def allocation_map(self) -> Dict[str, float]:
        return {variant.name: variant.allocation for variant in self.variants}

    def find_variant_by_name(self, name: str) -> VariantDefinition:
        for variant in self.variants:
            if variant.name == name:
                return variant
        raise ExperimentServiceError(f"Variant not found: {name}")

    def find_variant_by_id(self, variant_id: int) -> VariantDefinition:
        for variant in self.variants:
            if variant.id == variant_id:
                return variant
        raise ExperimentServiceError(f"Variant not found with id: {variant_id}")


@dataclass
class AssignmentResult:
    change_id: str
    experiment_id: str
    user_id: str
    variant_id: Optional[int]
    variant_name: Optional[Union[str, int]]
    is_control: bool
    out_of_experiment: bool
    property_values: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "experiment_id": self.experiment_id,
            "user_id": self.user_id,
            "variant_id": self.variant_id,
            "variant_name": self.variant_name,
            "is_control": self.is_control,
            "out_of_experiment": self.out_of_experiment,
            "property_values": self.property_values,
        }


class RemoteExperimentService:
    def __init__(
        self,
        config_base_url: str,
        exposure_base_url: Optional[str] = None,
        requester: Optional[Requester] = None,
    ):
        self.config_base_url = config_base_url.rstrip("/")
        self.exposure_base_url = exposure_base_url.rstrip("/") if exposure_base_url else None
        self.requester = requester or UrlRequester()
        self._cache: Dict[str, ExperimentConfig] = {}

    def fetch_experiment_config(self, change_id: str) -> ExperimentConfig:
        if change_id in self._cache:
            return self._cache[change_id]

        url = f"{self.config_base_url}/{change_id}"
        raw = self.requester.get_json(url)
        config = ExperimentConfig.from_api_response(change_id, raw)
        self._cache[change_id] = config
        return config

    def assign_user(
        self,
        user_id: str,
        change_id: str,
        property_name: Optional[str] = None,
    ) -> AssignmentResult:
        config = self.fetch_experiment_config(change_id)
        assigner = VariationAssigner(
            config.experiment_id,
            config.traffic_allocation,
            config.allocation_map(),
        )

        assigned_name = assigner.assign_variation(user_id)
        if assigned_name == "out of the experiment":
            return AssignmentResult(
                change_id=change_id,
                experiment_id=config.experiment_id,
                user_id=user_id,
                variant_id=None,
                variant_name=None,
                is_control=False,
                out_of_experiment=True,
                property_values={},
            )

        variant = config.find_variant_by_name(assigned_name)
        if config.properties:
            if property_name is None:
                property_name = config.properties[0]
            property_values = {
                key: variant.properties.get(key)
                for key in config.properties
                if key in variant.properties
            }
            return AssignmentResult(
                change_id=change_id,
                experiment_id=config.experiment_id,
                user_id=user_id,
                variant_id=variant.id,
                variant_name=variant.name,
                is_control=variant.is_control,
                out_of_experiment=False,
                property_values=property_values,
            )

        if config.properties:
            if property_name is None:
                property_name = config.properties[0]
            property_values = {
                key: variant.properties.get(key)
                for key in config.properties
                if key in variant.properties
            }
            return AssignmentResult(
                change_id=change_id,
                experiment_id=config.experiment_id,
                user_id=user_id,
                variant_id=variant.id,
                variant_name=variant.name,
                is_control=variant.is_control,
                out_of_experiment=False,
                property_values=property_values,
            )

        return AssignmentResult(
            change_id=change_id,
            experiment_id=config.experiment_id,
            user_id=user_id,
            variant_id=variant.id,
            variant_name=variant.id,
            is_control=variant.is_control,
            out_of_experiment=False,
            property_values={},
        )

    def log_exposure(
        self,
        assignment: AssignmentResult,
        exposure_url: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if exposure_url is None:
            exposure_url = self.exposure_base_url
        if not exposure_url:
            raise ExposurePostError("No exposure URL configured")

        payload = assignment.to_dict()
        if extra:
            payload.update(extra)

        return self.requester.post_json(exposure_url, payload)
