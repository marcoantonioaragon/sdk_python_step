from sdk_python_step.variation_assigner import RemoteExperimentService, AssignmentResult


class MockRequester:
    def __init__(self, config_data, exposure_response=None):
        self.config_data = config_data
        self.exposure_response = exposure_response or {"status": "ok"}
        self.last_post = None

    def get_json(self, url: str):
        return self.config_data

    def post_json(self, url: str, payload):
        self.last_post = {"url": url, "payload": payload}
        return self.exposure_response


def main():
    mock_api_response = {
        "experiment_id": "exp-2026-08-11",
        "traffic_allocation": 1,
        "variants": [
            {"id": 0, "name": "control", "allocation": 0.5,
                "is_control": True, "properties": {"button_color": "blue"}},
            {"id": 1, "name": "treatment", "allocation": 0.5,
                "is_control": False, "properties": {"button_color": "green"}},
        ],
        "properties": ["button_color"],
    }

    mock_requester = MockRequester(config_data=mock_api_response)
    service = RemoteExperimentService(
        config_base_url="https://api.example.com/experiment-config",
        exposure_base_url="https://api.example.com/exposure",
        requester=mock_requester,
    )

    user_id = "user_123"
    assignment = service.assign_user(user_id, change_id="change-abc")

    print("Assignment result:")
    print(assignment.to_dict())

    exposure_response = service.log_exposure(assignment)
    print("Exposure response:")
    print(exposure_response)

    print("Last POST payload:")
    print(mock_requester.last_post)


if __name__ == "__main__":
    main()
