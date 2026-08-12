import pytest
from sdk_python_step.variation_assigner import RemoteExperimentService, AssignmentResult


class DummyRequester:
    def __init__(self, config_data, exposure_response=None):
        self.config_data = config_data
        self.exposure_response = exposure_response or {"status": "ok"}
        self.last_post = None

    def get_json(self, url: str):
        return self.config_data

    def post_json(self, url: str, payload):
        self.last_post = {"url": url, "payload": payload}
        return self.exposure_response


def test_assign_user_returns_property_values_when_properties_defined():
    config_data = {
        "experiment_id": "exp-1",
        "traffic_allocation": 1.0,
        "variants": [
            {"id": 0, "name": "control", "allocation": 0.5,
                "is_control": True, "properties": {"color": "blue"}},
            {"id": 1, "name": "treatment", "allocation": 0.5,
                "is_control": False, "properties": {"color": "green"}},
        ],
        "properties": ["color"],
    }

    requester = DummyRequester(config_data)
    service = RemoteExperimentService(
        config_base_url="https://api.example.com/config",
        exposure_base_url="https://api.example.com/exposure",
        requester=requester,
    )

    assignment = service.assign_user("user1", change_id="change-1")

    assert assignment.variant_id in {0, 1}
    assert assignment.variant_name in {"control", "treatment"}
    assert assignment.property_values == {
        "color": "blue"} or assignment.property_values == {"color": "green"}
    assert not assignment.out_of_experiment


def test_assign_user_returns_variant_id_when_no_properties():
    config_data = {
        "experiment_id": "exp-2",
        "traffic_allocation": 1.0,
        "variants": [
            {"id": 0, "name": "control", "allocation": 0.5, "is_control": True},
            {"id": 1, "name": "treatment", "allocation": 0.5, "is_control": False},
        ],
        "properties": [],
    }

    requester = DummyRequester(config_data)
    service = RemoteExperimentService(
        config_base_url="https://api.example.com/config",
        exposure_base_url="https://api.example.com/exposure",
        requester=requester,
    )

    assignment = service.assign_user("user2", change_id="change-2")

    assert assignment.variant_id in {0, 1}
    assert assignment.variant_name in {0, 1}
    assert assignment.property_values == {}
    assert not assignment.out_of_experiment


def test_log_exposure_posts_payload_correctly():
    config_data = {
        "experiment_id": "exp-3",
        "traffic_allocation": 1.0,
        "variants": [
            {"id": 0, "name": "control", "allocation": 1.0, "is_control": True},
        ],
        "properties": [],
    }
    requester = DummyRequester(config_data)
    service = RemoteExperimentService(
        config_base_url="https://api.example.com/config",
        exposure_base_url="https://api.example.com/exposure",
        requester=requester,
    )

    assignment = service.assign_user("user3", change_id="change-3")
    response = service.log_exposure(assignment, extra={"source": "unit-test"})

    assert response == {"status": "ok"}
    assert requester.last_post["url"] == "https://api.example.com/exposure"
    assert requester.last_post["payload"]["source"] == "unit-test"
    assert requester.last_post["payload"]["variant_id"] == assignment.variant_id
