from sdk_python_step.variation_assigner import VariationAssigner
import pandas as pd


def main():
    # Example configuration
    experiment_id = "exp_123"
    traffic_alocation = 1  # 50% of users are in the experiment
    # Variations expressed as allocation fractions that sum to 1.0
    variations = {"control": 0.3, "treatment": 0.7}

    assigner = VariationAssigner(experiment_id, traffic_alocation, variations)

    # Example users: generate 30 users (user1..user30)
    users = [f"user{i+1}" for i in range(30000)]
    df = pd.DataFrame({"user_id": users})

    # Assign variations in batch
    df["variation"] = df["user_id"].apply(assigner.assign_variation)

    print(df.groupby('variation')['user_id'].nunique()/len(users))


if __name__ == "__main__":
    main()
